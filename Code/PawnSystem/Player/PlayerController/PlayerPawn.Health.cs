using Sandbox.Events;

namespace Facepunch;

public partial class PlayerPawn : IGameEventHandler<DamageGivenEvent>, IGameEventHandler<DamageTakenEvent>
{
	private TimeSince _timeSinceLastDamage = float.MaxValue;

	/// <summary>
	/// Called from OnUpdate. Regenerates health once you stop taking damage, hardcore included (you patch yourself up).
	/// Hardcore's arm wounds stay; a shot leg heals by itself (HealthComponent.Wounds.cs).
	/// </summary>
	internal void UpdateHealthRegen()
	{
		if ( !Networking.IsHost ) return;
		var mode = GameMode.Instance;
		if ( !mode.IsValid() ) return;
		if ( HealthComponent.State != LifeState.Alive ) return;
		if ( HealthComponent.Health >= HealthComponent.MaxHealth ) return;

		// Zombies: CoD-style fast regen, but never while downed.
		var zombies = ZombiesPlayerState.For( this );
		if ( zombies is { IsDowned: true } ) return;

		// Multiplayer: full health back in ~4s once you stop taking damage, unless a custom game says otherwise.
		var regen = zombies is not null ? (3f, 40f) : CustomGameSettings.ActiveRules.RegenSpeed;
		if ( regen is not { } speed ) return;

		var (delay, rate) = speed;
		if ( _timeSinceLastDamage < delay ) return;

		HealthComponent.Health = Math.Min( HealthComponent.MaxHealth,
			HealthComponent.Health + rate * Time.Delta );
	}

	/// <summary>
	/// Where the damage indicator points: where the damage came from, or null for none.
	/// - A blast's Position is its centre, and a burn's the heat's source, so they point there.
	/// - A bullet's or a blade's Position is where it struck you, inches from your own eye, which is no direction at all:
	///   a round from behind that clipped the arms or the gun held out in front showed as a hit from the front. So they
	///   point back along the round's path (Force is its direction).
	/// - A zombie's claw has no direction (Position is your own middle), so it points at the zombie.
	/// - Falls and other damage you did yourself show none.
	/// </summary>
	private Vector3? IndicatorSource( DamageInfo info )
	{
		if ( info.Flags.HasFlag( DamageFlags.FallDamage ) )
			return null;

		if ( info.Flags.HasFlag( DamageFlags.Explosion ) || info.Flags.HasFlag( DamageFlags.Burn ) )
			return info.Position;

		if ( !info.Force.IsNearZeroLength )
			return info.Position - info.Force.Normal * 2000f;

		var attacker = info.Attacker;
		if ( attacker.IsValid() && attacker.GameObject.Root != GameObject.Root )
			return attacker.WorldPosition;

		return null;
	}

	/// <summary>
	/// Called when YOU inflict damage on something
	/// </summary>
	void IGameEventHandler<DamageGivenEvent>.OnGameEvent( DamageGivenEvent eventArgs )
	{
		// Did we cause this damage?
		if ( IsViewer )
		{
			Crosshair.Instance?.Trigger( eventArgs.DamageInfo );
		}
	}

	/// <summary>
	/// Called when YOU take damage from something
	/// </summary>
	void IGameEventHandler<DamageTakenEvent>.OnGameEvent( DamageTakenEvent eventArgs )
	{
		var damageInfo = eventArgs.DamageInfo;

		var attacker = GameUtils.GetPlayerFromComponent( eventArgs.DamageInfo.Attacker );
		var victim = GameUtils.GetPlayerFromComponent( eventArgs.DamageInfo.Victim );
		var attackerIsViewer = attacker.IsValid() && attacker.IsViewer;
		var victimIsViewer = victim.IsValid() && victim.IsViewer;
		var botOnlyDamage = attacker.IsValid() && attacker.Client.IsValid() && attacker.Client.IsBot
			&& victim.IsValid() && victim.Client.IsValid() && victim.Client.IsBot;

		if ( botOnlyDamage )
			return;

		var position = eventArgs.DamageInfo.Position;

		// A burn is heat on the skin, not a hit: no flinch, knock or blood. It holds off regen like any damage, and the
		// indicator shows where the heat comes from.
		if ( damageInfo.Flags.HasFlag( DamageFlags.Burn ) )
		{
			_timeSinceLastDamage = 0f;
			if ( IsViewer && IndicatorSource( damageInfo ) is { } heat )
				DamageIndicator.Current?.OnHit( heat );
			return;
		}

		var force = damageInfo.Force.IsNearZeroLength ? Random.Shared.VectorInSphere() : damageInfo.Force;

		if ( Body.IsValid() && Body.AnimationHelpers is not null )
		{
			foreach ( var helper in Body.AnimationHelpers )
			{
				helper.ProceduralHitReaction( damageInfo.Damage / 100f, force );
			}
		}

		// The zone has no attacker, but standing in it mustn't let health come back.
		if ( damageInfo.Flags.HasFlag( DamageFlags.Zone ) )
			_timeSinceLastDamage = 0f;

		if ( !damageInfo.Attacker.IsValid() )
			return;

		// Is this the local player?
		if ( IsViewer && IndicatorSource( damageInfo ) is { } source )
		{
			DamageIndicator.Current?.OnHit( source );
		}

		_timeSinceLastDamage = 0f;

		TimeUntilAccelerationRecovered = Global.TakeDamageAccelerationDampenTime;
		AccelerationAddedScale = Global.TakeDamageAccelerationOffset;

		if ( attacker != victim && Body.IsValid() )
		{
			Body.DamageTakenPosition = position;
			Body.DamageTakenForce = force.Normal * damageInfo.Damage * Game.Random.Float( 5f, 20f );
		}

		// Headshot effects
		if ( damageInfo.Hitbox.HasFlag( HitboxTags.Head ) )
		{
			// Non-local viewer
			if ( !IsViewer )
			{
				var go = damageInfo.HasHelmet ? HeadshotWithHelmetEffect?.Clone( position ) : HeadshotEffect?.Clone( position );
				if ( go.IsValid() && !go.Components.Get<DestroyAfter>().IsValid() )
					go.DestroyAsync( 2f );
			}

			var headshotSound = damageInfo.HasHelmet ? HeadshotWithHelmetSound : HeadshotSound;
			if ( headshotSound is not null )
			{
				var handle = Sound.Play( headshotSound, position );
				handle.SpacialBlend = (attackerIsViewer || victimIsViewer) ? 0 : handle.SpacialBlend;
			}
		}
		else
		{
			// Non-local viewer: our own body isn't drawn, so the blood would float around the camera.
			if ( !IsViewer && BloodEffect.IsValid() )
			{
				var blood = BloodEffect?.Clone( new CloneConfig()
				{
					StartEnabled = true,
					Transform = new( position ),
					Name = $"Blood effect from ({GameObject})"
				} );

				if ( blood.IsValid() && !blood.Components.Get<DestroyAfter>().IsValid() )
					blood.DestroyAsync( 2f );
			}

			// A fall isn't a hit: the landing has its own sound. A knife's stab isn't a bullet's thwack.
			var impactSound = damageInfo.Flags.HasFlag( DamageFlags.Melee ) ? WorldSounds.KnifeFlesh ?? BloodImpactSound : BloodImpactSound;
			if ( impactSound is not null && !damageInfo.Flags.HasFlag( DamageFlags.FallDamage ) )
			{
				var snd = Sound.Play( impactSound, position );
				if ( !snd.IsValid() ) return;

				snd.SpacialBlend = IsViewer ? 0 : snd.SpacialBlend;
			}
		}
	}
}
