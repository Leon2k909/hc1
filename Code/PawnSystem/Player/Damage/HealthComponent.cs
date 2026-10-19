using Facepunch.UI;
using Sandbox;
using Sandbox.Diagnostics;
using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A health component for any kind of GameObject.
/// </summary>
public partial class HealthComponent : Component, IRespawnable//, Component.IDamageable
{
	private const float FriendlyBulletHealthFraction = 0.5f;

	/// <summary>
	/// Are we in god mode?
	/// </summary>
	[Property, Sync( SyncFlags.FromHost )] public bool IsGodMode { get; set; } = false;

	/// <summary>
	/// An action (mainly for ActionGraphs) to respond to when a GameObject's health changes.
	/// </summary>
	[Property] public Action<float, float> OnHealthChanged { get; set; }

	/// <summary>
	/// How long has it been since life state changed?
	/// </summary>
	public TimeSince TimeSinceLifeStateChanged { get; private set; } = 1f;

	/// <summary>
	/// A list of all Respawnable things on this GameObject
	/// </summary>
	protected IEnumerable<IRespawnable> Respawnables => GetComponents<IRespawnable>();

	protected IEnumerable<IDamageListener> DamageListeners => GetComponents<IDamageListener>();

	/// <summary>
	/// What's our health?
	/// </summary>
	[Sync( SyncFlags.FromHost ), Change( nameof( OnHealthPropertyChanged ) )]
	public float Health { get; set; } = 100f;

	/// <summary>Synced, since a custom game can change the soldiers' (CustomGameSettings.ApplyMaxHealth) and the HUD shows health against it.</summary>
	[Property, Group( "Setup" ), Sync( SyncFlags.FromHost )]
	public float MaxHealth { get; set; } = 100f;

	/// <summary>
	/// What's our life state?
	/// </summary>
	[Group( "Life State" ), Sync( SyncFlags.FromHost ), Change( nameof( OnStatePropertyChanged ) )]
	public LifeState State { get; private set; }

	/// <summary>
	/// Called when <see cref="Health"/> is changed across the network.
	/// </summary>
	/// <param name="oldValue"></param>
	/// <param name="newValue"></param>
	protected void OnHealthPropertyChanged( float oldValue, float newValue )
	{
		OnHealthChanged?.Invoke( oldValue, newValue );
	}

	protected void OnStatePropertyChanged( LifeState oldValue, LifeState newValue )
	{
		TimeSinceLifeStateChanged = 0f;
	}

	protected override void OnStart()
	{
		Health = MaxHealth;
	}

	// public void OnDamage( in Sandbox.DamageInfo damage )
	// {
	// 	TakeDamage( Tec.Utils.CreateDamageInfo( damage ) );
	// }
	
	public void TakeDamage( DamageInfo damageInfo )
	{
		Assert.True( Networking.IsHost );

		// In hardcore mode, explosions and knives to or from a bot kill outright, regardless of armor.
		// Use the same component-owner lookup as kill scoring so child health components
		// are still recognized as part of a lightweight bot.
		var isHardcore = GameMode.IsHardcore;
		var isHcBot = isHardcore &&
			          GameUtils.GetLightweightBotFromComponent( this ) is not null;
		var isHcBotAttackOnPlayer = isHardcore &&
			                       GameUtils.GetPlayerFromComponent( this ) is not null &&
			                       GameUtils.GetLightweightBotFromComponent( damageInfo.Attacker ) is not null;

		var gunDamage = damageInfo.Damage;
		damageInfo = WithThisAsVictim( damageInfo );

		// A custom game's rules can turn off teammates' damage, or every bullet that isn't to the head or neck.
		if ( IsRuledOut( damageInfo ) )
			return;

		damageInfo = ModifyDamage( damageInfo );

		// Hardcore bullets go by where they hit (HealthComponent.Wounds.cs). Explosions and knives to or from a bot still
		// kill outright. The battle royale's zone and burns only ever wear health down.
		var hurt = damageInfo.Damage > 0f;
		var bullet = isHardcore && hurt && IsBulletHit( damageInfo );
		var friendlyBullet = hurt && IsFriendlySoldierBullet( damageInfo );
		var lethal = hurt && damageInfo.WasExplosion && damageInfo.SeveredLimbs != BlastLimb.None;
		if ( bullet && !friendlyBullet )
			damageInfo = HardcoreBullet( damageInfo, gunDamage, out lethal );
		else if ( isHardcore && hurt && !friendlyBullet && (isHcBot || isHcBotAttackOnPlayer)
			&& !damageInfo.Flags.HasFlag( DamageFlags.Zone ) && !damageInfo.Flags.HasFlag( DamageFlags.Burn ) )
			lethal = true;

		if ( IsGodMode || DevCommands.NoDamage )
		{
			BroadcastDamage( damageInfo );
			return;
		}

		var armor = GameUtils.GetPlayerFromComponent( this )?.ArmorComponent;
		if ( armor is { ArmorEnabled: true } && damageInfo.ArmorDamage > 0f
			&& (!bullet || !damageInfo.Hitbox.HasFlag( HitboxTags.Head )) )
		{
			// Protection cannot absorb more than the vest's remaining condition.
			var absorbed = Math.Min( armor.Armor, damageInfo.ArmorDamage );
			armor.Armor = Math.Max( 0f, armor.Armor - absorbed );
			damageInfo = damageInfo with { Damage = damageInfo.Damage + damageInfo.ArmorDamage - absorbed, ArmorDamage = absorbed };
		}

		if ( damageInfo.RemoveHelmet && armor is { HelmetsEnabled: true } )
			armor.HasHelmet = false;

		if ( friendlyBullet )
		{
			// Two unarmoured friendly bullet hits from full health, even to the head. Preserve the share blocked by armour,
			// and never let the hardcore instant-kill roll turn an accidental first hit into a team kill.
			lethal = false;
			var totalDamage = damageInfo.Damage + damageInfo.ArmorDamage;
			var unblocked = totalDamage > 0f ? Math.Clamp( damageInfo.Damage / totalDamage, 0f, 1f ) : 0f;
			damageInfo = damageInfo with { Damage = MaxHealth * FriendlyBulletHealthFraction * unblocked };
		}

		BroadcastDamage( damageInfo );

		if ( bullet && State == LifeState.Alive && IsLimbHit( damageInfo ) )
			AddWound( damageInfo.Hitbox );

		// Landing hard enough to hurt lames the legs the same way, in every mode (fall damage always hits the legs).
		if ( hurt && damageInfo.WasFallDamage && State == LifeState.Alive )
			AddWound( damageInfo.Hitbox );

		if ( lethal && State == LifeState.Alive )
		{
			Health = 0f;
			State = LifeState.Dead;
			Kill( damageInfo );
			return;
		}

		Health = Math.Max( 0f, Health - damageInfo.Damage );

		if ( Health > 0f || State != LifeState.Alive ) return;

		Health = 0f;
		State = LifeState.Dead;

		Kill( damageInfo );
	}

	/// <summary>Only bullets between different allied soldiers use the two-hit friendly-fire rule.</summary>
	private bool IsFriendlySoldierBullet( DamageInfo damageInfo )
	{
		if ( !IsBulletHit( damageInfo ) || !damageInfo.Attacker.IsValid()
			|| damageInfo.Attacker.GameObject.Root == GameObject.Root )
			return false;

		var team = GameUtils.GetTeamFromComponent( this );
		if ( team == Team.Unassigned || team != GameUtils.GetTeamFromComponent( damageInfo.Attacker ) )
			return false;

		return (GameUtils.GetPlayerFromComponent( this ).IsValid() || GameUtils.GetLightweightBotFromComponent( this ).IsValid())
			&& (GameUtils.GetPlayerFromComponent( damageInfo.Attacker ).IsValid()
				|| GameUtils.GetLightweightBotFromComponent( damageInfo.Attacker ).IsValid());
	}

	/// <summary>
	/// Damage a custom game's rules (CustomGameSettings) leave out: a teammate's with friendly fire off (your own still
	/// counts), and with headshots only, a bullet anywhere but the head or neck. It's dropped before anyone hears of it,
	/// so there's no hitmarker either.
	/// </summary>
	private bool IsRuledOut( DamageInfo damageInfo )
	{
		var rules = CustomGameSettings.ActiveRules;

		if ( rules.HeadshotsOnly && IsBulletHit( damageInfo ) && (damageInfo.Hitbox & HeadOrNeck) == 0 )
			return true;

		if ( !rules.FriendlyFire && damageInfo.Attacker.IsValid() && damageInfo.Attacker.GameObject.Root != GameObject.Root )
		{
			var attackerTeam = GameUtils.GetTeamFromComponent( damageInfo.Attacker );
			if ( attackerTeam != Team.Unassigned && attackerTeam == GameUtils.GetTeamFromComponent( this ) )
				return true;
		}

		return false;
	}

	private DamageInfo WithThisAsVictim( DamageInfo damageInfo )
	{
		var extraFlags = DamageFlags.None;
		var hitbox = damageInfo.Hitbox;

		if ( damageInfo.WasExplosion || damageInfo.WasMelee ) hitbox = HitboxTags.UpperBody;
		if ( damageInfo.WasFallDamage ) hitbox = HitboxTags.Leg;

		return damageInfo with
		{
			Victim = this,
			Hitbox = hitbox,
			Flags = damageInfo.Flags | extraFlags
		};
	}

	private DamageInfo ModifyDamage( DamageInfo damageInfo )
	{
		damageInfo = ModifyDamage<ModifyDamageGivenEvent>( damageInfo.Attacker?.GameObject.Root, damageInfo );
		damageInfo = ModifyDamage<ModifyDamageTakenEvent>( damageInfo.Victim?.GameObject.Root, damageInfo );
		damageInfo = ModifyDamage<ModifyDamageGlobalEvent>( Scene, damageInfo );

		return damageInfo;
	}

	private static DamageInfo ModifyDamage<T>( GameObject root, DamageInfo damageInfo )
		where T : ModifyDamageEvent, new()
	{
		if ( root is null )
		{
			return damageInfo;
		}

		var modifyEvent = new T { DamageInfo = damageInfo };

		root.Dispatch( modifyEvent );

		return modifyEvent.DamageInfo;
	}

	private void BroadcastDamage( DamageInfo damageInfo )
	{
		BroadcastDamage( damageInfo.Damage, damageInfo.Position, damageInfo.Force,
			damageInfo.Attacker, damageInfo.Inflictor,
			damageInfo.Hitbox, damageInfo.Flags );
	}

	private void Kill( DamageInfo damageInfo )
	{
		BroadcastKill( damageInfo.Damage, damageInfo.Position, damageInfo.Force,
			damageInfo.Attacker, damageInfo.Inflictor,
			damageInfo.Hitbox, damageInfo.Flags, damageInfo.SeveredLimbs );

		KillFeed.RecordEvent( damageInfo );
	}

	[Rpc.Broadcast]
	private void BroadcastDamage( float damage, Vector3 position, Vector3 force, Component attacker, Component inflictor = default, HitboxTags hitbox = default, DamageFlags flags = default )
	{
		Component victim = GameUtils.GetPlayerFromComponent( this );
		if ( !victim.IsValid() )
		{
			victim = GameUtils.GetLightweightBotFromComponent( this );
		}

		if ( !victim.IsValid() )
		{
			victim = this;
		}

		var damageInfo = new DamageInfo( attacker, damage, inflictor, position, force, hitbox, flags )
		{
			Victim = victim
		};

		GameObject.Root.Dispatch( new DamageTakenEvent( damageInfo ) );

		Scene.Dispatch( new DamageTakenGlobalEvent( damageInfo ) );

		if ( damageInfo.Attacker.IsValid() )
		{
			damageInfo.Attacker.GameObject.Root.Dispatch( new DamageGivenEvent( damageInfo ) );
		}

		DamageListeners.ToList().ForEach( x => x.OnDamaged( damageInfo ) );
	}

	[Rpc.Broadcast]
	private void BroadcastKill( float damage, Vector3 position, Vector3 force, Component attacker, Component inflictor = default, HitboxTags hitbox = default, DamageFlags flags = default, BlastLimb severedLimbs = BlastLimb.None )
	{
		var damageInfo = new DamageInfo( attacker, damage, inflictor, position, force, hitbox, flags )
		{
			Victim = this,
			SeveredLimbs = flags.HasFlag( DamageFlags.Explosion ) ? severedLimbs : BlastLimb.None
		};

		Scene.Dispatch( new KillEvent( damageInfo ) );

		Respawnables.ToList().ForEach( x => x.OnKill( damageInfo ) );
	}
}

/// <summary>
/// The component's life state.
/// </summary>
public enum LifeState
{
	Alive,
	Dead
}

/// <summary>
/// A respawnable object.
/// </summary>
public interface IRespawnable
{
	public void OnRespawn() { }
	public void OnKill( DamageInfo damageInfo ) { }
}

public interface IDamageListener
{
	public void OnDamaged( DamageInfo damageInfo ) { }
}
