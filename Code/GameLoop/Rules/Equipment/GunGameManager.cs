using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Manages Gun Game progression (CoD-style).
/// Each kill advances the killer to the next weapon tier.
/// Knife is the FINAL tier - getting a knife kill wins the game.
/// Getting killed by a knife demotes the victim one tier.
/// </summary>
public sealed class GunGameManager : Component,
	IGameEventHandler<KillEvent>,
	IGameEventHandler<EnterStateEvent>,
	IGameEventHandler<ResetScoresEvent>
{
	/// <summary>
	/// Ordered list of weapons (first = starting weapon, last = win weapon - should be knife).
	/// </summary>
	[Property]
	public List<EquipmentResource> WeaponProgression { get; set; } = new();

	/// <summary>
	/// Synced dictionary of PlayerPawn component Guid -> current tier index.
	/// </summary>
	[Sync( SyncFlags.FromHost )]
	public NetDictionary<Guid, int> PlayerTiers { get; private set; } = new();

	/// <summary>
	/// If true, getting killed by a knife demotes victim one tier.
	/// </summary>
	[Property]
	public bool KnifeKillsDemote { get; set; } = true;

	/// <summary>
	/// Knife equipment resource - kills with this weapon win the game / demote.
	/// </summary>
	[Property]
	public EquipmentResource KnifeResource { get; set; }

	/// <summary>
	/// Total number of tiers in the progression.
	/// </summary>
	public int TotalTiers => WeaponProgression.Count;

	/// <summary>
	/// Gets the current tier index for a player (0 = first weapon).
	/// </summary>
	public int GetPlayerTier( PlayerPawn player )
	{
		if ( !player.IsValid() ) return 0;
		return PlayerTiers.GetValueOrDefault( player.Id, 0 );
	}

	/// <summary>
	/// Gets the EquipmentResource for a given tier index.
	/// </summary>
	public EquipmentResource GetWeaponForTier( int tier )
	{
		if ( WeaponProgression.Count == 0 ) return null;
		return WeaponProgression[Math.Clamp( tier, 0, WeaponProgression.Count - 1 )];
	}

	/// <summary>
	/// Clears inventory and gives the player exactly their tier weapon (no backup knife).
	/// </summary>
	private void GivePlayerWeapon( PlayerPawn player, EquipmentResource weapon )
	{
		if ( !player.IsValid() || weapon is null ) return;

		// Clear all carried weapons
		player.Inventory.Clear();

		// Give only the current tier weapon
		player.Inventory.Give( weapon, false );
		player.Inventory.SwitchToBest();
	}

	/// <summary>
	/// Called when any state is entered - give players their current tier weapons after respawn.
	/// </summary>
	[After<RespawnPlayers>]
	void IGameEventHandler<EnterStateEvent>.OnGameEvent( EnterStateEvent eventArgs )
	{
		if ( !Networking.IsHost ) return;

		foreach ( var player in GameUtils.PlayerPawns )
		{
			var tier = GetPlayerTier( player );
			GivePlayerWeapon( player, GetWeaponForTier( tier ) );
		}
	}

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		if ( !Networking.IsHost ) return;

		var damageInfo = eventArgs.DamageInfo;

		var killerPlayer = GameUtils.GetPlayerFromComponent( damageInfo.Attacker );
		var victimPlayer = GameUtils.GetPlayerFromComponent( damageInfo.Victim );

		// Need valid distinct players
		if ( !killerPlayer.IsValid() || !victimPlayer.IsValid() ) return;
		if ( killerPlayer == victimPlayer ) return;

		// Check if the kill was done with the knife
		bool killedWithKnife = KnifeResource is not null
		                       && damageInfo.Inflictor is Equipment killerWeapon
		                       && killerWeapon.Resource == KnifeResource;

		// ── Victim demotion ──────────────────────────────────────────────────
		if ( killedWithKnife && KnifeKillsDemote )
		{
			var victimTier = PlayerTiers.GetValueOrDefault( victimPlayer.Id, 0 );
			if ( victimTier > 0 )
			{
				var demotedTier = victimTier - 1;
				PlayerTiers[victimPlayer.Id] = demotedTier;
				GivePlayerWeapon( victimPlayer, GetWeaponForTier( demotedTier ) );
				BroadcastTierChanged( victimPlayer, demotedTier, false );
			}
		}

		// ── Killer advancement ───────────────────────────────────────────────
		var currentTier = PlayerTiers.GetValueOrDefault( killerPlayer.Id, 0 );
		var nextTier = currentTier + 1;

		// If the player is already on the last tier AND killed with knife → WIN
		if ( currentTier == TotalTiers - 1 && killedWithKnife )
		{
			PlayerTiers[killerPlayer.Id] = TotalTiers;
			BroadcastWin( killerPlayer );
			return;
		}

		// If they've now passed all tiers without a knife kill (shouldn't normally happen)
		if ( nextTier >= TotalTiers )
		{
			nextTier = TotalTiers - 1; // Stay on the knife tier
		}

		PlayerTiers[killerPlayer.Id] = nextTier;
		GivePlayerWeapon( killerPlayer, GetWeaponForTier( nextTier ) );
		BroadcastTierChanged( killerPlayer, nextTier, true );
	}

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent eventArgs )
	{
		if ( !Networking.IsHost ) return;
		PlayerTiers.Clear();
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void BroadcastTierChanged( PlayerPawn player, int newTier, bool advanced )
	{
		if ( !player.IsValid() ) return;

		var weaponName = GetWeaponForTier( newTier )?.Name ?? "Unknown";
		var playerName = player.Client?.DisplayName ?? "Unknown";

		var msg = advanced
			? "{0} → {1} (Tier {2}/{3})"
			: "{0} was demoted to {1}";

		// Every machine shows this itself, and the toast puts the English in its player's language.
		Facepunch.UI.Toast.Instance?.Show( msg, Facepunch.UI.ToastType.Generic, 5f, playerName, weaponName, newTier + 1, TotalTiers );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void BroadcastWin( PlayerPawn winner )
	{
		if ( !winner.IsValid() ) return;

		var name = winner.Client?.DisplayName ?? "Unknown";
		Facepunch.UI.Toast.Instance?.Show( "🏆 {0} won Gun Game!", Facepunch.UI.ToastType.Generic, 5f, name );

		if ( Networking.IsHost )
		{
			// Transition to the next state (Game Over)
			var sm = GameMode.Instance?.StateMachine;
			if ( sm.IsValid() && sm.CurrentState.IsValid() )
			{
				var nextState = sm.CurrentState.DefaultNextState;
				if ( nextState.IsValid() )
					sm.Transition( nextState );
			}
		}
	}

	/// <summary>
	/// Give the correct tier weapon to a player when they respawn.
	/// </summary>
	public void OnPlayerRespawned( PlayerPawn player )
	{
		if ( !Networking.IsHost ) return;
		var tier = GetPlayerTier( player );
		GivePlayerWeapon( player, GetWeaponForTier( tier ) );
	}
}
