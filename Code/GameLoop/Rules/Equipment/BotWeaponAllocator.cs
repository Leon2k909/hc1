using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Allocates primary weapons to bots when they spawn
/// </summary>
public sealed class BotWeaponAllocator : Component,
	IGameEventHandler<PlayerSpawnedEvent>
{
	/// <summary>
	/// List of primary weapons that bots can use per team
	/// </summary>
	[Property] public List<Loadout> TeamLoadouts { get; set; }

	/// <summary>
	/// Get available weapons for a specific team
	/// </summary>
	private List<EquipmentResource> GetWeaponsForTeam( Team team )
	{
		if ( TeamLoadouts.FirstOrDefault( x => x.Team == team ) is { } loadout )
		{
			return loadout.Equipment;
		}

		// Fallback to first loadout if no team-specific one exists
		return TeamLoadouts.FirstOrDefault()?.Equipment ?? new();
	}

	// The body is a named method: hotload can't re-link static lambdas inside explicit generic interface methods
	// ("Unable to find matching substitution for a static method"), so they'd throw after every hotload.
	void IGameEventHandler<PlayerSpawnedEvent>.OnGameEvent( PlayerSpawnedEvent eventArgs ) => ArmBot( eventArgs );

	void ArmBot( PlayerSpawnedEvent eventArgs )
	{
		var player = eventArgs.Player;

		// Only handle bot spawns
		if ( !player.Client.IsBot )
			return;

		// Get weapons available for bot's team
		var availableWeapons = GetWeaponsForTeam( player.Team );
		if ( availableWeapons.Count == 0 )
			return;

		// Pick a random primary weapon
		var primaryWeapons = availableWeapons.Where( w => w.Slot == EquipmentSlot.Primary );
		if ( !primaryWeapons.Any() )
			return;

		// Select random weapon and give to bot
		var randomWeapon = primaryWeapons.OrderBy( x => Random.Shared.Next() ).First();
		player.Inventory.Give( randomWeapon, true );
	}
}
