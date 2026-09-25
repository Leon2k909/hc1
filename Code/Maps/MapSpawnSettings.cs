namespace Facepunch;

/// <summary>
/// Per-map spawn rules, for maps whose own spawns don't suit our modes. Innocent Hotel is a TTT map: every
/// info_player_start is in one lobby room, and its basement and roof are only reachable through TTT teleporters
/// we don't have, so the scene places its own team spawns and turns both of these off.
/// </summary>
public sealed class MapSpawnSettings : Component
{
	/// <summary>
	/// Also spawn players and bots at the map's own info_player_starts.
	/// </summary>
	[Property] public bool UseMapSpawnPoints { get; set; } = true;

	/// <summary>
	/// Let bots spawn at random navmesh points. Turn off when parts of the navmesh can't be walked to.
	/// </summary>
	[Property] public bool AllowNavMeshSpawns { get; set; } = true;

	public static MapSpawnSettings Current => Game.ActiveScene?.GetAllComponents<MapSpawnSettings>().FirstOrDefault();

	public static bool MapSpawnPointsAllowed => Current?.UseMapSpawnPoints ?? true;
	public static bool NavMeshSpawnsAllowed => Current?.AllowNavMeshSpawns ?? true;
}
