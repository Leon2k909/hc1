using Sandbox.Events;

namespace Facepunch;

public partial class PlayerPawn : IGameEventHandler<DamageGivenEvent>, IGameEventHandler<DamageTakenEvent>
{
	private TimeSince _timeSinceLastDamage = float.MaxValue;

	/// <summary>
	/// Called from OnUpdate. Regenerates health slowly when in Core (non-hardcore) mode.
	/// </summary>
	internal void UpdateHealthRegen()
	{
		if ( !Networking.IsHost ) return;
		var mode = GameMode.Instance;
		if ( !mode.IsValid() || mode.Hardcore ) return;
		if ( HealthComponent.State != LifeState.Alive ) return;
		if ( HealthComponent.Health >= HealthComponent.MaxHealth ) return;
		if ( _timeSinceLastDamage < 5f ) return;

		HealthComponent.Health = Math.Min( HealthComponent.MaxHealth,
			HealthComponent.Health + 2f * Time.Delta );
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
		var force = damageInfo.Force.IsNearZeroLength ? Random.Shared.VectorInSphere() : damageInfo.Force;

		if ( Body.IsValid() && Body.AnimationHelpers is not null )
		{
			foreach ( var helper in Body.AnimationHelpers )
			{
				helper.ProceduralHitReaction( damageInfo.Damage / 100f, force );
			}
		}

		if ( !damageInfo.Attacker.IsValid() )
			return;

		// Is this the local player?
		if ( IsViewer )
		{
			DamageIndicator.Current?.OnHit( position );
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
			if ( BloodEffect.IsValid() )
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

			if ( BloodImpactSound is not null )
			{
				var snd = Sound.Play( BloodImpactSound, position );
				if ( !snd.IsValid() ) return;

				snd.SpacialBlend = IsViewer ? 0 : snd.SpacialBlend;
			}
		}
	}
}
