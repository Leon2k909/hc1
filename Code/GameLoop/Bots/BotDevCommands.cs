namespace Facepunch;

/// <summary>
/// Stress testing with lots of bots: fill a map with them, then measure the frame time.
/// </summary>
public static class BotDevCommands
{
	/// <summary>
	/// Log frame times, bot time, allocations and the engine's own timings over the next <paramref name="frames"/>
	/// frames. Compare runs with <c>bot_lod_off 1</c> and <c>0</c>.
	/// </summary>
	[ConCmd( "dev_perf" )]
	public static void Perf( int frames = 300 )
	{
		var system = BotSystem.Current;
		if ( system is null )
		{
			Log.Warning( "dev_perf: no BotSystem in this scene (load a map first)" );
			return;
		}

		system.StartSampling( frames );
	}

	/// <summary>
	/// Host: add <paramref name="count"/> bots for the rest of the match. With a <paramref name="radius"/> they're spread
	/// over the navmesh up to that far from you, otherwise they spawn the usual way.
	/// </summary>
	[ConCmd( "dev_bots" )]
	public static void Bots( int count = 50, float radius = 0f )
	{
		var manager = LightweightBotManager.Instance;
		if ( !manager.IsValid() )
		{
			Log.Warning( "dev_bots: no bot manager (this mode doesn't fill with bots)" );
			return;
		}

		var spawned = manager.DevSpawnBots( count, radius );
		Log.Info( $"dev_bots: spawned {spawned} of {count}" );
	}

	/// <summary> Host: log every living bot's fighting style and habits, its skill, gun and what it's doing in its fight. </summary>
	[ConCmd( "dev_bot_styles" )]
	public static void BotStyles()
	{
		var bots = Game.ActiveScene?.GetAllComponents<LightweightCombatBot>().Where( x => x.IsValid() && x.IsAlive )
			.OrderBy( x => x.Team ).ThenBy( x => x.BotName ).ToList();
		if ( bots is not { Count: > 0 } )
		{
			Log.Info( "dev_bot_styles: no bots" );
			return;
		}

		foreach ( var bot in bots )
		{
			var habits = bot.Habits;
			Log.Info( $"{bot.BotName} ({bot.Team}): {habits.Style}, skill {bot.Skill:0.00}, aggression {bot.Aggression:0.00}, "
				+ $"range {bot.PreferredRange * habits.Range:0}, strafe {habits.StrafeLeg:0.00}s, plant {habits.Plant:0.00}s, "
				+ $"patience {habits.Patience:0.0}s, {bot.WeaponResource?.ResourceName ?? "?"}, move {bot.CurrentMove}" );
		}

		foreach ( var group in bots.GroupBy( x => x.Habits.Style ) )
			Log.Info( $"dev_bot_styles: {group.Key} x{group.Count()}" );
	}

	/// <summary> Host: remove every bot. The mode's own bot fill puts its usual number back. </summary>
	[ConCmd( "dev_bots_clear" )]
	public static void ClearBots()
	{
		LightweightBotManager.Instance?.DevClearBots();
	}

	/// <summary>
	/// Start a match of a mode on a map, e.g. <c>dev_mode deathmatch flatgrass</c> or <c>dev_mode battle_royale flatgrass</c>.
	/// <paramref name="mode"/> is the prefab's name under prefabs/game_modes/, or a mode's ident.
	/// </summary>
	[ConCmd( "dev_mode" )]
	public static void Mode( string mode = "deathmatch", string mapContains = "flatgrass" )
	{
		var map = ResourceLibrary.GetAll<SceneFile>()
			.FirstOrDefault( s => s.ResourcePath?.Contains( mapContains, StringComparison.OrdinalIgnoreCase ) ?? false );
		if ( map is null )
		{
			Log.Warning( $"dev_mode: no map matching '{mapContains}'" );
			return;
		}

		var gameMode = GameObject.GetPrefab( $"prefabs/game_modes/{mode}.prefab" )?.GetComponent<GameMode>()
			?? GameMode.GetAll( map ).FirstOrDefault( x => string.Equals( x.Ident, mode, StringComparison.OrdinalIgnoreCase ) );
		if ( !gameMode.IsValid() )
		{
			Log.Warning( $"dev_mode: no mode '{mode}'" );
			return;
		}

		Facepunch.UI.MatchLauncher.StartMatch( gameMode, map );
	}
}

public sealed partial class LightweightBotManager
{
	/// <summary>
	/// dev_bots: <paramref name="count"/> more bots for the rest of the match, split between the teams (or all against
	/// all), spread over the navmesh up to <paramref name="radius"/> from the local player, or spawned the usual way
	/// with no radius. Host only.
	/// </summary>
	public int DevSpawnBots( int count, float radius )
	{
		if ( Networking.IsActive && !Networking.IsHost )
			return 0;

		var centre = Client.Local?.PlayerPawn?.WorldPosition ?? Vector3.Zero;
		var spawned = 0;
		for ( var i = 0; i < count; i++ )
		{
			var team = GameUtils.IsFreeForAllMode ? Team.Unassigned : (i % 2 == 0 ? Team.Terrorist : Team.CounterTerrorist);
			Transform? at = null;
			for ( var attempt = 0; radius > 0f && attempt < 8 && at is null; attempt++ )
			{
				if ( Scene.NavMesh.GetRandomPoint( centre, radius ) is not { } point )
					continue;
				if ( point.Distance( centre ) < 600f || !IsOnMainNavMesh( point ) )
					continue;

				at = new Transform( point, Rotation.FromYaw( Random.Shared.Float( 0f, 360f ) ) );
			}

			_teamBotAdjustment[team] = GetAdjustment( team ) + 1;
			if ( SpawnBot( team, at ).IsValid() )
				spawned++;
		}

		return spawned;
	}

	/// <summary> dev_bots_clear: every bot out, and the dev_bots and scoreboard additions forgotten. Host only. </summary>
	public void DevClearBots()
	{
		_teamBotAdjustment.Clear();
		ClearBots();
	}
}
