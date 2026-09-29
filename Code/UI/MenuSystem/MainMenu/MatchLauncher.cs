using System.Threading.Tasks;

namespace Facepunch.UI;

/// <summary>
/// Starts a match from the main menu: the hub's featured screen, its map picker and the Popular Playlists row. The map
/// vote's "play a different mode" starts one from a match, leaving its lobby first (<see cref="LeaveAndStart"/>).
/// </summary>
public static class MatchLauncher
{
	/// <summary>Loads the map in the mode.</summary>
	public static void StartMatch( GameMode mode, SceneFile map )
	{
		if ( mode is null || map is null ) return;

		// Core modes are off for now, every match is hardcore, except Zombies, which has its own rules. Put back with
		// Core: GameMode.SetHardcore( the player's Core / Hardcore choice ), which the removed Multiplayer page
		// (LandingPage) had a commented-out toggle for.
		GameMode.SetCurrent( mode );
		GameMode.SetHardcore( !IsZombies( mode ) );
		Game.ActiveScene.Load( map );
	}

	/// <summary>
	/// Leaves the lobby the player is in, if any, then starts <paramref name="mode"/> on <paramref name="map"/> in a lobby
	/// of their own, which GameNetworkManager makes when the map loads, as for a match started from the menu. False if
	/// the old lobby is still closing after 5 s.
	/// </summary>
	public static async Task<bool> LeaveAndStart( GameMode mode, SceneFile map )
	{
		if ( mode is null || map is null ) return false;

		if ( Networking.IsActive )
		{
			Networking.Disconnect();
			for ( var attempt = 0; attempt < 100 && Networking.IsActive; attempt++ )
				await GameTask.DelaySeconds( 0.05f );

			if ( Networking.IsActive ) return false;
		}

		// A normal match, as from the menu, which clears a custom game's settings too.
		CustomGameSettings.Reset();
		StartMatch( mode, map );
		return true;
	}

	public static bool IsZombies( GameMode mode ) => string.Equals( mode?.Ident, "zombies", StringComparison.OrdinalIgnoreCase );

	public static GameMode ZombiesMode() => GameObject.GetPrefab( "prefabs/game_modes/zombies.prefab" )?.GetComponent<GameMode>();

	/// <summary>Match maps that can host Zombies, Flatgrass first since it was the original.</summary>
	public static List<SceneFile> ZombiesMaps()
	{
		var mode = ZombiesMode();
		if ( !mode.IsValid() ) return new();

		return GameUtils.GetMatchMaps()
			.Where( m => GameMode.GetAll( m ).Any( x => x.Ident == mode.Ident ) )
			.OrderByDescending( m => m.ResourcePath?.Contains( "flatgrass", StringComparison.OrdinalIgnoreCase ) ?? false )
			.ToList();
	}

	public static GameMode BattleRoyaleMode() => GameObject.GetPrefab( BattleRoyaleMatch.ModePrefab )?.GetComponent<GameMode>();
}
