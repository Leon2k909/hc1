using Sandbox;
using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// CoD-style zombies perks. Stored as flags so they sync as one value.
/// </summary>
[Flags]
public enum ZombiesPerk
{
	None = 0,
	IronTonic = 1,
	BoltSoda = 2,
	HotShot = 4,
	SecondWind = 8,
	FleetFoot = 16,
}

/// <summary>
/// Per-player zombies state: downed / bleed-out / revive, and perks.
/// Lives on the player pawn next to <see cref="ZombiesPlayerEconomy"/>.
/// </summary>
public sealed class ZombiesPlayerState : Component, IUse,
	IGameEventHandler<ModifyDamageTakenEvent>
{
	public const float BaseMaxHealth = 100f;
	public const float IronTonicMaxHealth = 250f;
	public const float BleedOutTime = 30f;
	public const float ReviveTime = 4f;
	public const float SecondWindReviveTime = 2f;
	public const float SoloSelfReviveTime = 8f;
	public const float ReviveRange = 110f;

	[Sync( SyncFlags.FromHost )] public bool IsDowned { get; private set; }
	[Sync( SyncFlags.FromHost )] public ZombiesPerk Perks { get; private set; }
	[Sync( SyncFlags.FromHost )] public float ReviveProgress { get; private set; }
	[Sync( SyncFlags.FromHost )] public PlayerPawn Reviver { get; private set; }

	/// <summary>Time since going down (valid while <see cref="IsDowned"/>).</summary>
	[Sync( SyncFlags.FromHost )] public TimeSince TimeSinceDowned { get; private set; }

	/// <summary>Solo with Second Wind: you get back up by yourself (uses up the perk).</summary>
	[Sync( SyncFlags.FromHost )] public bool IsSelfReviving { get; private set; }

	public PlayerPawn Player => GetComponent<PlayerPawn>();

	public float BleedOutRemaining => IsDowned ? Math.Max( 0f, BleedOutTime - TimeSinceDowned ) : 0f;

	public bool HasPerk( ZombiesPerk perk ) => (Perks & perk) != 0;

	private bool _allowDeath;
	private Component _lastDamageAttacker;

	public static ZombiesPlayerState For( Component c )
	{
		var pawn = c as PlayerPawn ?? c?.GetComponentInParent<PlayerPawn>();
		return pawn.IsValid() ? pawn.GetComponent<ZombiesPlayerState>() : null;
	}

	// ── Perk effect helpers used by weapon / movement code ──────────────────────
	public static float ReloadScale( PlayerPawn owner ) =>
		For( owner ) is { } s && s.HasPerk( ZombiesPerk.BoltSoda ) ? 0.5f : 1f;

	public static float FireDelayScale( PlayerPawn owner ) =>
		For( owner ) is { } s && s.HasPerk( ZombiesPerk.HotShot ) ? 0.75f : 1f;

	public static float MoveSpeedScale( PlayerPawn owner )
	{
		if ( For( owner ) is not { } s ) return 1f;
		if ( s.IsDowned ) return 0.4f;
		return s.HasPerk( ZombiesPerk.FleetFoot ) ? 1.15f : 1f;
	}

	// ── Perks ───────────────────────────────────────────────────────────────────
	public void GivePerk( ZombiesPerk perk )
	{
		if ( !Networking.IsHost ) return;
		Perks |= perk;
		ApplyPerkStats();
	}

	private void ClearPerks()
	{
		Perks = ZombiesPerk.None;
		ApplyPerkStats();
	}

	private void ApplyPerkStats()
	{
		var hc = Player?.HealthComponent;
		if ( !hc.IsValid() ) return;

		var max = HasPerk( ZombiesPerk.IronTonic ) ? IronTonicMaxHealth : BaseMaxHealth;
		var gained = max > hc.MaxHealth;
		hc.MaxHealth = max;
		hc.Health = gained ? max : Math.Min( hc.Health, max );
	}

	// ── Damage → downed instead of dead ────────────────────────────────────────
	void IGameEventHandler<ModifyDamageTakenEvent>.OnGameEvent( ModifyDamageTakenEvent e )
	{
		if ( !Networking.IsHost || _allowDeath ) return;
		if ( e.DamageInfo.Attacker?.GetComponentInParent<ZombieAI>() is { } zombie )
			_lastDamageAttacker = zombie;

		var hc = Player?.HealthComponent;
		if ( !hc.IsValid() || hc.State != LifeState.Alive ) return;

		// God mode / no-damage skip the health change after this event, so don't go down either.
		if ( hc.IsGodMode || DevCommands.NoDamage ) return;

		if ( IsDowned )
		{
			// Zombies ignore downed players, but stray damage shouldn't finish you either.
			e.ClearDamage();
			return;
		}

		AbsorbWithArmor( e );

		if ( hc.Health - e.DamageInfo.Damage <= 0f )
		{
			var canSelfRevive = ZombiesRoundSystem.CountHumanPlayers() <= 1
				&& HasPerk( ZombiesPerk.SecondWind );
			// Without a rescue option, let the lethal hit kill normally.
			if ( !canSelfRevive && !HasPotentialReviver() ) return;

			e.DamageInfo = e.DamageInfo with { Damage = Math.Max( 0f, hc.Health - 1f ) };
			GoDown();
		}
	}

	/// <summary>
	/// Armour plates bought at the workbench (<see cref="ZombiesBuyStation.PlateArmor"/>) take the damage first, point for
	/// point, like CoD's plates. Falls land on the legs, and fire burns what plates don't cover, so they go straight
	/// through.
	/// </summary>
	private void AbsorbWithArmor( ModifyDamageTakenEvent e )
	{
		var armor = Player?.ArmorComponent;
		if ( !armor.IsValid() || armor.Armor <= 0f || e.DamageInfo.WasFallDamage ) return;
		if ( e.DamageInfo.Flags.HasFlag( DamageFlags.Burn ) ) return;

		var absorbed = Math.Min( armor.Armor, e.DamageInfo.Damage );
		if ( absorbed <= 0f ) return;

		armor.Armor -= absorbed;
		e.DamageInfo = e.DamageInfo with { Damage = e.DamageInfo.Damage - absorbed };
	}

	private bool HasPotentialReviver() => Scene.GetAllComponents<PlayerPawn>().Any( pawn =>
		pawn != Player && pawn.IsValid() && pawn.Client.IsValid()
		&& pawn.Client.IsConnected && !pawn.Client.IsBot
		&& pawn.HealthComponent.IsValid() && pawn.HealthComponent.State == LifeState.Alive
		&& (For( pawn ) is not { IsDowned: true } || For( pawn ).IsSelfReviving) );

	private void GoDown()
	{
		IsDowned = true;
		TimeSinceDowned = 0;
		ReviveProgress = 0;
		Reviver = null;
		var hadSecondWind = _hadSecondWind || HasPerk( ZombiesPerk.SecondWind );
		ClearPerks();

		var solo = ZombiesRoundSystem.CountHumanPlayers() <= 1;
		IsSelfReviving = solo && hadSecondWind;
		_hadSecondWind = false;

		Log.Info( $"[Zombies] {Player?.DisplayName} went down (solo={solo}, selfRevive={IsSelfReviving})" );
		ZombiesRoundSystem.Current?.OnPlayerDowned( this );
	}

	// Tracked separately because ClearPerks() runs before the solo check.
	private bool _hadSecondWind;

	private void Revive()
	{
		Log.Info( $"[Zombies] {Player?.DisplayName} revived" );
		IsDowned = false;
		IsSelfReviving = false;
		ReviveProgress = 0;
		Reviver = null;

		var hc = Player?.HealthComponent;
		if ( hc.IsValid() ) hc.Health = hc.MaxHealth;
	}

	/// <summary>Host: fully reset for a new game or a fresh spawn.</summary>
	public void ResetState()
	{
		if ( !Networking.IsHost ) return;
		if ( IsDowned || Perks != ZombiesPerk.None ) Log.Info( $"[Zombies] {Player?.DisplayName} state reset (was downed={IsDowned}, perks={Perks})" );
		IsDowned = false;
		IsSelfReviving = false;
		ReviveProgress = 0;
		Reviver = null;
		_hadSecondWind = false;
		ClearPerks();
	}

	/// <summary>Host: bring a downed player back up instantly (round restart etc).</summary>
	public void ForceRevive()
	{
		if ( Networking.IsHost && IsDowned ) Revive();
	}

	private void BleedOut()
	{
		Log.Info( $"[Zombies] {Player?.DisplayName} bled out" );
		IsDowned = false;
		IsSelfReviving = false;
		Reviver = null;
		ReviveProgress = 0;

		var hc = Player?.HealthComponent;
		if ( !hc.IsValid() ) return;

		_allowDeath = true;
		hc.TakeDamage( new DamageInfo( _lastDamageAttacker.IsValid() ? _lastDamageAttacker : this, 99999f ) );
		_allowDeath = false;
		_lastDamageAttacker = null;
	}

	protected override void OnUpdate()
	{
		if ( !Networking.IsHost ) return;

		// Remember Second Wind so a solo player can self-revive after going down.
		if ( HasPerk( ZombiesPerk.SecondWind ) ) _hadSecondWind = true;

		if ( !IsDowned ) return;

		if ( IsSelfReviving )
		{
			ReviveProgress = (TimeSinceDowned / SoloSelfReviveTime).Clamp( 0f, 1f );
			if ( ReviveProgress >= 1f ) Revive();
			return;
		}

		// A teammate dying or disconnecting can remove the last rescue option.
		if ( ZombiesRoundSystem.Current?.IsGameOver == true || !HasPotentialReviver() )
		{
			BleedOut();
			return;
		}

		// Reviver has to keep holding use and stay close.
		if ( Reviver.IsValid() )
		{
			var stillReviving = Reviver.IsUsing
				&& Reviver.HealthComponent.State == LifeState.Alive
				&& !(For( Reviver )?.IsDowned ?? false)
				&& Reviver.WorldPosition.Distance( WorldPosition ) < ReviveRange;

			if ( stillReviving )
			{
				var time = For( Reviver )?.HasPerk( ZombiesPerk.SecondWind ) == true ? SecondWindReviveTime : ReviveTime;
				ReviveProgress += Time.Delta / time;
				if ( ReviveProgress >= 1f )
				{
					if ( Reviver.GetComponent<ZombiesPlayerEconomy>() is { } eco ) eco.AddPoints( 100 );
					Revive();
				}
				return;
			}

			Reviver = null;
			ReviveProgress = 0;
		}

		if ( TimeSinceDowned > BleedOutTime )
			BleedOut();
	}

	// ── IUse: teammates press E on a downed player to revive ─────────────────────
	UseResult IUse.CanUse( PlayerPawn player )
	{
		if ( !IsDowned || player == Player ) return false;
		if ( For( player )?.IsDowned == true ) return false;
		return true;
	}

	void IUse.OnUse( PlayerPawn player )
	{
		if ( !Networking.IsHost || !IsDowned ) return;
		Reviver = player;
	}
}
