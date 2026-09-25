namespace Facepunch;

partial class GameMode
{
	/// <summary>
	/// Gets all game modes referenced by a scene.
	/// </summary>
	public static IEnumerable<GameMode> GetAll( SceneFile scene )
	{
		return GetGameModesForScene( scene );
	}

	private static IEnumerable<GameMode> GetGameModesForScene( SceneFile scene )
	{
		var list = new List<GameMode>();
		var meta = scene.GetMetadata( "GameModes", "" );

		if ( !string.IsNullOrEmpty( meta ) )
		{
			var files = meta.Split( ", " );

			foreach ( var file in files )
			{
				AddGameMode( list, file );
			}
		}

		if ( GameUtils.IsMainMenuMap( scene ) )
		{
			AddGameMode( list, "prefabs/game_modes/deathmatch.prefab" );
			AddGameMode( list, "prefabs/game_modes/team_deathmatch.prefab" );
			// Defuse and Retakes need bomb sites placed in the scene, so only maps that list Defuse get them.
			if ( meta.Contains( "bomb_defusal", StringComparison.OrdinalIgnoreCase ) )
			{
				AddGameMode( list, "prefabs/game_modes/bomb_defusal.prefab" );
				AddGameMode( list, "prefabs/game_modes/retakes.prefab" );
			}
			AddGameMode( list, "prefabs/game_modes/gun_game.prefab" );
			AddGameMode( list, "prefabs/game_modes/cash_grab.prefab" );
			AddGameMode( list, "prefabs/game_modes/domination.prefab" );
			AddGameMode( list, "prefabs/game_modes/hardpoint.prefab" );
			AddGameMode( list, "prefabs/game_modes/gunfight_1v1.prefab" );
			AddGameMode( list, "prefabs/game_modes/gunfight_2v2.prefab" );
			AddGameMode( list, "prefabs/game_modes/zombies.prefab" );
		}

		if ( list.Any( x => x.Ident == "tdm" || x.Ident == "dm" ) )
		{
			if ( !list.Any( x => x.Ident == "domination" ) )
			{
				AddGameMode( list, "prefabs/game_modes/domination.prefab" );
			}
			if ( !list.Any( x => x.Ident == "hardpoint" ) )
			{
				AddGameMode( list, "prefabs/game_modes/hardpoint.prefab" );
			}
			if ( !list.Any( x => x.Ident == "gunfight_1v1" ) )
			{
				AddGameMode( list, "prefabs/game_modes/gunfight_1v1.prefab" );
			}
			if ( !list.Any( x => x.Ident == "gunfight_2v2" ) )
			{
				AddGameMode( list, "prefabs/game_modes/gunfight_2v2.prefab" );
			}
		}

		return list;
	}

	private static void AddGameMode( List<GameMode> list, string file )
	{
		var prefab = GameObject.GetPrefab( file );
		if ( !prefab.IsValid() )
			return;

		var gameMode = prefab.GetComponent<GameMode>();
		if ( gameMode.IsValid() && !list.Any( x => x.Ident.Equals( gameMode.Ident, StringComparison.OrdinalIgnoreCase ) ) )
		{
			list.Add( gameMode );
		}
	}

	internal static string GetPrefabPath( GameMode gameMode )
	{
		if ( !gameMode.IsValid() )
			return null;

		var source = gameMode.GameObject.PrefabInstanceSource;
		if ( !string.IsNullOrWhiteSpace( source ) )
			return source;

		return gameMode.Ident switch
		{
			"defuse" => "prefabs/game_modes/bomb_defusal.prefab",
			"cashgrab" => "prefabs/game_modes/cash_grab.prefab",
			"dm" => "prefabs/game_modes/deathmatch.prefab",
			"retakes" => "prefabs/game_modes/retakes.prefab",
			"tdm" => "prefabs/game_modes/team_deathmatch.prefab",
			"gun_game" => "prefabs/game_modes/gun_game.prefab",
			"domination" => "prefabs/game_modes/domination.prefab",
			"hardpoint" => "prefabs/game_modes/hardpoint.prefab",
			"zombies" => "prefabs/game_modes/zombies.prefab",
			"gunfight_1v1" => "prefabs/game_modes/gunfight_1v1.prefab",
			"gunfight_2v2" => "prefabs/game_modes/gunfight_2v2.prefab",
			_ => null
		};
	}

	public static IReadOnlyList<GameMode> AllUnique
	{
		get
		{
			var list = new List<GameMode>();
			var scenes = GameUtils.GetAvailableMaps();

			foreach ( var scene in scenes )
			{
				var modes = GetAll( scene );
				foreach ( var mode in modes )
				{
					if ( !list.Any( x => x.Ident.Equals( mode.Ident, StringComparison.OrdinalIgnoreCase ) ) )
					{
						list.Add( mode );
					}
				}
			}

			return list.ToList()
				.AsReadOnly();
		}
	}
}
