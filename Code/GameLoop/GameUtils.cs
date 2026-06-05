namespace Facepunch;

public interface IWeighted
{
	float Weight { get; }
}

/// <summary>
/// A list of game utilities that'll help us achieve common goals with less code... I guess?
/// </summary>
public static partial class GameUtils
{
	/// <summary>
	/// All players in the game (includes disconnected players before expiration).
	/// </summary>
	public static IEnumerable<Client> AllPlayers => Game.ActiveScene?.GetAllComponents<Client>() ?? Enumerable.Empty<Client>();

	/// <summary>
	/// Get all players on a team.
	/// </summary>
	public static IEnumerable<Client> GetPlayers( Team team ) => AllPlayers.Where( x => x.Team == team );

	/// <summary>
	/// Every <see cref="PlayerPawn"/> currently in the world.
	/// </summary>
	public static IEnumerable<PlayerPawn> PlayerPawns
	{
		get
		{
			var clientPawns = AllPlayers.Select( x => x.PlayerPawn );
			var scenePawns = Game.ActiveScene?.GetAllComponents<PlayerPawn>() ?? Enumerable.Empty<PlayerPawn>();
			return clientPawns.Concat( scenePawns ).Where( x => x.IsValid() ).Distinct();
		}
	}

	/// <summary>
	/// Every <see cref="PlayerPawn"/> currently in the world, on the given team.
	/// </summary>
	public static IEnumerable<PlayerPawn> GetPlayerPawns( Team team ) => PlayerPawns.Where( x => x.Team == team );

	public static IEnumerable<LightweightCombatBot> LightweightBots => Game.ActiveScene?.GetAllComponents<LightweightCombatBot>() ?? Enumerable.Empty<LightweightCombatBot>();

	public static IEnumerable<LightweightCombatBot> GetLightweightBots( Team team ) => LightweightBots.Where( x => x.Team == team );

	public static bool IsFreeForAllMode => string.Equals( GameMode.Instance?.Ident, "dm", StringComparison.OrdinalIgnoreCase );

	public static int GetMatchParticipantCount()
	{
		var players = AllPlayers.Count( x => x.IsConnected && !x.IsBot && (IsFreeForAllMode || x.Team != Team.Unassigned) );
		var bots = LightweightBots.Count( x => x.IsAlive && (IsFreeForAllMode || x.Team != Team.Unassigned) );
		return players + bots;
	}

	public static bool IsCombatFrozen => GameMode.Instance?.Get<FreezePlayers>() is not null;

	public static bool IsGunsmithStudioOpen() => GunsmithPanel.IsAnyOpen;

	public static bool IsInteractiveMouseUiOpen() =>
		Facepunch.UI.PauseMenuPanel.IsAnyOpen
		|| Facepunch.UI.BuyMenu.IsAnyOpen
		|| Facepunch.UI.Chat.IsAnyOpen
		|| Input.Down( "Score" )
		|| Facepunch.UI.EndOfMatchScreen.IsAnyVisible;

	public static PlayerPawn GetActiveCombatPawn()
	{
		var client = GetActiveClient();
		var pawn = client?.Pawn as PlayerPawn;

		if ( IsActiveCombatPlayer( pawn ) )
			return pawn;

		pawn = client?.PlayerPawn;

		if ( IsActiveCombatPlayer( pawn ) )
			return pawn;

		return PlayerPawns.FirstOrDefault( IsActiveCombatPlayer );
	}

	public static bool IsActiveCombatPlayer( PlayerPawn player )
	{
		if ( !player.IsValid() )
			return false;

		return IsPlayerViewerSafe( player ) || IsPlayerLocallyControlledSafe( player );
	}

	public static bool ShouldHideCombatMouse( PlayerPawn player = null )
	{
		player ??= GetActiveCombatPawn();

		return GetCombatMouseBlockReason( player ) is null;
	}

	public static string GetCombatMouseBlockReason( PlayerPawn player = null )
	{
		if ( !player.IsValid() )
		{
			if ( GameMode.Instance.IsValid() && !IsGunsmithStudioOpen() && !IsInteractiveMouseUiOpen() )
				return null;

			return "no valid player";
		}

		if ( !IsActiveCombatPlayer( player ) )
			return "player is not the active viewer/local pawn";

		if ( !player.HealthComponent.IsValid() )
			return "missing health component";

		if ( player.HealthComponent.State != LifeState.Alive )
			return $"player is {player.HealthComponent.State}";

		if ( IsGunsmithStudioOpen() )
			return "gunsmith open";

		if ( Facepunch.UI.PauseMenuPanel.IsAnyOpen )
			return "pause menu open";

		if ( Facepunch.UI.BuyMenu.IsAnyOpen )
			return "buy menu open";

		if ( Facepunch.UI.Chat.IsAnyOpen )
			return "chat open";

		if ( Input.Down( "Score" ) )
			return "scoreboard open";

		if ( Facepunch.UI.EndOfMatchScreen.IsAnyVisible )
			return "end of match screen visible";

		return null;
	}

	public static void UpdateCombatMouseVisibility( PlayerPawn player = null )
	{
		if ( ShouldHideCombatMouse( player ) )
		{
			Mouse.Visible = false;
			Mouse.CursorType = "none";
			Mouse.Visibility = MouseVisibility.Hidden;
			return;
		}

		Mouse.Visible = true;
		Mouse.CursorType = null;

		// Force Visible for the gunsmith only: there the cursor must stay put while
		// right-click-dragging to pan. Everywhere else (in-game menus, dead/spectate)
		// stay on Auto so the engine can manage the cursor normally — forcing Visible
		// in-game made it "stick" on screen after a right-click.
		Mouse.Visibility = IsGunsmithStudioOpen() ? MouseVisibility.Visible : MouseVisibility.Auto;
	}

	[ConCmd( "hc1_mouse_debug" )]
	private static void Command_MouseDebug()
	{
		var player = GetActiveCombatPawn();
		var blockReason = GetCombatMouseBlockReason( player );
		UpdateCombatMouseVisibility( player );

		Log.Info(
			$"MouseDebug: visibility={Mouse.Visibility}, visible={GetMouseVisibleDebug()}, cursor={GetMouseCursorDebug()}, active={GetMouseActiveDebug()}, position={GetMousePositionDebug()}, hide={blockReason is null}, reason={blockReason ?? "none"}, " +
			$"lockShouldCapture={Facepunch.UI.CombatMouseLock.LastShouldCapture}, lockHasCapture={Facepunch.UI.CombatMouseLock.LastHasMouseCapture}, " +
			$"lockHasFocus={Facepunch.UI.CombatMouseLock.LastHasFocus}, " +
			$"player={GetPlayerDisplayNameDebug( player )}, isViewer={GetPlayerViewerDebug( player )}, " +
			$"isLocal={GetPlayerLocalDebug( player )}, gameMode={GetGameModeDebug()}, gunsmith={IsGunsmithStudioOpen()}, " +
			$"pause={Facepunch.UI.PauseMenuPanel.IsAnyOpen}, buy={Facepunch.UI.BuyMenu.IsAnyOpen}, " +
			$"chat={Facepunch.UI.Chat.IsAnyOpen}, score={Input.Down( "Score" )}, end={Facepunch.UI.EndOfMatchScreen.IsAnyVisible}" );
	}

	private static Client GetActiveClient()
	{
		var viewer = Client.Viewer;
		if ( viewer is not null && viewer.IsValid() )
			return viewer;

		var local = Client.Local;
		if ( local is not null && local.IsValid() )
			return local;

		return viewer ?? local;
	}

	private static bool IsPlayerViewerSafe( PlayerPawn player )
	{
		try
		{
			return player.IsViewer;
		}
		catch
		{
			return false;
		}
	}

	private static bool IsPlayerLocallyControlledSafe( PlayerPawn player )
	{
		try
		{
			return player.IsLocallyControlled;
		}
		catch
		{
			return false;
		}
	}

	private static string GetPlayerDisplayNameDebug( PlayerPawn player )
	{
		if ( !player.IsValid() )
			return "null";

		try
		{
			return player.DisplayName ?? "null";
		}
		catch ( Exception exception )
		{
			return $"error:{exception.GetType().Name}";
		}
	}

	private static string GetPlayerViewerDebug( PlayerPawn player )
	{
		if ( !player.IsValid() )
			return "null";

		try
		{
			return player.IsViewer.ToString();
		}
		catch ( Exception exception )
		{
			return $"error:{exception.GetType().Name}";
		}
	}

	private static string GetPlayerLocalDebug( PlayerPawn player )
	{
		if ( !player.IsValid() )
			return "null";

		try
		{
			return player.IsLocallyControlled.ToString();
		}
		catch ( Exception exception )
		{
			return $"error:{exception.GetType().Name}";
		}
	}

	private static string GetMouseActiveDebug()
	{
		try
		{
			return Mouse.Active.ToString();
		}
		catch ( Exception exception )
		{
			return $"error:{exception.GetType().Name}";
		}
	}

	private static string GetMouseVisibleDebug()
	{
		try
		{
			return Mouse.Visible.ToString();
		}
		catch ( Exception exception )
		{
			return $"error:{exception.GetType().Name}";
		}
	}

	private static string GetMouseCursorDebug()
	{
		try
		{
			return Mouse.CursorType ?? "null";
		}
		catch ( Exception exception )
		{
			return $"error:{exception.GetType().Name}";
		}
	}

	private static string GetMousePositionDebug()
	{
		try
		{
			return Mouse.Position.ToString();
		}
		catch ( Exception exception )
		{
			return $"error:{exception.GetType().Name}";
		}
	}

	private static string GetGameModeDebug()
	{
		var gameMode = GameMode.Instance;

		if ( !gameMode.IsValid() )
			return "none";

		return string.IsNullOrWhiteSpace( gameMode.Ident ) ? gameMode.GetType().Name : gameMode.Ident;
	}

	public static int GetAliveTeamMemberCount( Team team )
	{
		var players = GetPlayerPawns( team ).Count( x => x.HealthComponent.State == LifeState.Alive );
		var bots = GetLightweightBots( team ).Count( x => x.IsAlive );
		return players + bots;
	}

	public static IDescription GetDescription( GameObject go )
	{
		if ( !go.IsValid() )
			return null;

		return go.GetComponent<IDescription>() ?? go.Root.GetComponent<IDescription>();
	}

	public static IDescription GetDescription( Component component ) => GetDescription( component?.GameObject );

	public static Team GetTeamFromComponent( Component component )
	{
		if ( component is ITeam directTeam && directTeam.IsValid )
		{
			return directTeam.Team;
		}

		if ( !component.IsValid() || !component.GameObject.IsValid() )
		{
			return Team.Unassigned;
		}

		if ( component.GameObject.Root.GetComponent<ITeam>() is { IsValid: true } team )
		{
			return team.Team;
		}

		if ( component.GameObject.Root.GetComponent<Client>() is { IsValid: true } client )
		{
			return client.Team;
		}

		return Team.Unassigned;
	}

	private static readonly string[] MainMenuMapOrder = { "Refinery", "Flatgrass", "Depot", "Aesthetic Mall" };

	/// <summary>Maps currently excluded from quick play / lobby selection (work in progress).</summary>
	private static readonly HashSet<string> DisabledMaps = new( StringComparer.OrdinalIgnoreCase )
	{
		"Refinery",
	};

	public static IEnumerable<SceneFile> GetAvailableMaps()
	{
		return ResourceLibrary.GetAll<SceneFile>()
			.Where( IsMainMenuMap )
			.Where( m => !DisabledMaps.Contains( m.GetMetadata( "Title", m.ResourceName ) ) )
			.OrderBy( GetMainMenuMapOrder );
	}

	internal static bool IsMainMenuMap( SceneFile map )
	{
		var title = map.GetMetadata( "Title", "" );
		if ( MainMenuMapOrder.Any( x => string.Equals( x, title, StringComparison.OrdinalIgnoreCase ) ) )
		{
			return true;
		}

		var path = map.ResourcePath ?? "";
		return path.Contains( "scenes/maps/refinery/refinery.scene", StringComparison.OrdinalIgnoreCase )
			|| path.Contains( "scenes/maps/flatgrass/flatgrass.scene", StringComparison.OrdinalIgnoreCase )
			|| path.Contains( "scenes/maps/depot/depot.scene", StringComparison.OrdinalIgnoreCase );
	}

	private static int GetMainMenuMapOrder( SceneFile map )
	{
		var title = map.GetMetadata( "Title", "" );
		for ( var i = 0; i < MainMenuMapOrder.Length; i++ )
		{
			if ( string.Equals( MainMenuMapOrder[i], title, StringComparison.OrdinalIgnoreCase ) )
			{
				return i;
			}
		}

		return MainMenuMapOrder.Length;
	}

	/// <summary>
	/// Get all spawn point transforms for the given team.
	/// </summary>
	public static IEnumerable<SpawnPointInfo> GetSpawnPoints( Team team, params string[] tags ) => Game.ActiveScene
		.GetAllComponents<TeamSpawnPoint>()
		.Where( x => x.Team == team )
		.Where( x => tags.Length == 0 || tags.Any( x.Tags.Contains ) )
		.Select( x => new SpawnPointInfo( x.Transform.World, x.GameObject.Tags.ToArray() ) )
		.Concat( Game.ActiveScene.GetAllComponents<SpawnPoint>()
			.Select( x => new SpawnPointInfo( x.Transform.World, x.GameObject.Tags.ToArray() ) ) );

	/// <summary>
	/// Get all spawn point transforms
	/// </summary>
	public static IEnumerable<SpawnPointInfo> GetSpawnPoints( params string[] tags ) => Game.ActiveScene
		.GetAllComponents<TeamSpawnPoint>()
		.Where( x => tags.Length == 0 || tags.Any( x.Tags.Contains ) )
		.Select( x => new SpawnPointInfo( x.Transform.World, x.GameObject.Tags.ToArray() ) )
		.Concat( Game.ActiveScene.GetAllComponents<SpawnPoint>()
			.Select( x => new SpawnPointInfo( x.Transform.World, x.GameObject.Tags.ToArray() ) ) );

	/// <summary>
	/// Pick a random spawn point for the given team.
	/// </summary>
	public static SpawnPointInfo GetRandomSpawnPoint( Team team, params string[] tags )
	{
		return Random.Shared.FromArray( GetSpawnPoints( team, tags ).ToArray(),
			new SpawnPointInfo( Transform.Zero, Array.Empty<string>() ) );
	}

	/// <summary>
	/// Helper list of the two teams.
	/// </summary>
	public static IReadOnlyList<Team> Teams { get; } = new[] { Team.Terrorist, Team.CounterTerrorist };

	/// <summary>
	/// Get a player from a component that belongs to a player or their descendants.
	/// </summary>
	public static PlayerPawn GetPlayerFromComponent( Component component )
	{
		if ( component is PlayerPawn player ) return player;
		if ( !component.IsValid() ) return null;
		return !component.GameObject.IsValid() ? null : component.GameObject.Root.GetComponentInChildren<PlayerPawn>();
	}

	public static LightweightCombatBot GetLightweightBotFromComponent( Component component )
	{
		if ( component is LightweightCombatBot bot ) return bot;
		if ( !component.IsValid() ) return null;
		return !component.GameObject.IsValid() ? null : component.GameObject.Root.GetComponentInChildren<LightweightCombatBot>();
	}

	/// <summary>
	/// Get a player from a component that belongs to a player or their descendants.
	/// </summary>
	public static Pawn GetPawn( Component component )
	{
		if ( component is Pawn pawn ) return pawn;
		if ( !component.IsValid() ) return null;
		return !component.GameObject.IsValid() ? null : component.GameObject.Root.GetComponentInChildren<Pawn>();
	}

	public static Equipment FindEquipment( Component inflictor )
	{
		if ( inflictor is Equipment equipment )
		{
			return equipment;
		}

		return null;
	}

	/// <summary>
	/// Returns the invoking client to the main menu
	/// </summary>
	public static void ReturnToMainMenu()
	{
		var sc = ResourceLibrary.Get<SceneFile>( "scenes/menu.scene" );
		Game.ActiveScene.Load( sc );
	}

	/// <summary>
	/// Log all known player states to the console.
	/// </summary>
	public static void LogPlayers()
	{
		/*
		var writer = new StringWriter();

		writer.WriteLine( "All players:" );

		foreach ( var player in AllPlayers )
		{
			writer.WriteLine( $"  {player.GameObject.Name}:" );
			writer.WriteLine( $"    Id: {player.Id}" );
			writer.WriteLine( $"    DisplayName: {player.DisplayName}" );
			writer.WriteLine( $"    IsConnected: {player.IsConnected}" );
			writer.WriteLine( $"    IsLocalPlayer: {player.IsLocalPlayer}" );
			writer.WriteLine( $"    Connection: {(player.Connection is { } connection ? $"{connection.Id} ({connection.DisplayName})" : "null")}" );
			writer.WriteLine( $"    Team: {player.Team}" );
			writer.WriteLine( $"    UniqueId: {player.PlayerId?.UniqueId}" );
			writer.WriteLine( $"    TeamUniqueId: {player.PlayerId?.TeamUniqueId}" );
			writer.WriteLine( $"    PlayerPawn: {player.PlayerPawn?.Id.ToString() ?? "null"}" );
		}

		writer.WriteLine();
		writer.WriteLine( "All pawns:" );

		foreach ( var pawn in Game.ActiveScene.GetAllComponents<PlayerPawn>() )
		{
			writer.WriteLine( $"  {pawn.GameObject.Name}:" );
			writer.WriteLine( $"    Id: {pawn.Id}" );
			writer.WriteLine( $"    DisplayName: {pawn.DisplayName}" );
			writer.WriteLine( $"    Client: {pawn.Client?.Id.ToString() ?? "null"}" );
		}

		writer.WriteLine();
		writer.WriteLine( "All connections:" );

		foreach ( var connection in Connection.All )
		{
			writer.WriteLine( $"  {connection.Name}:" );
			writer.WriteLine( $"    Id: {connection.Id}" );
			writer.WriteLine( $"    DisplayName: {connection.DisplayName}" );
			writer.WriteLine( $"    PartyId: {connection.PartyId}" );
			writer.WriteLine( $"    SteamId: {connection.SteamId}" );
			writer.WriteLine( $"    IsConnecting: {connection.IsConnecting}" );
			writer.WriteLine( $"    IsActive: {connection.IsActive}" );
		}

		Log.Info( writer.ToString() );
		*/
	}

	public static T FromListWeighted<T>( this Random random, IReadOnlyList<T> list, T defaultValue = default )
		where T : IWeighted
	{
		if ( list.Count == 0 )
		{
			return defaultValue;
		}

		var totalWeight = list.Sum( x => x.Weight );

		if ( totalWeight <= 0f )
		{
			return defaultValue;
		}

		var value = random.NextSingle() * totalWeight;

		foreach ( var item in list )
		{
			if ( item.Weight < 0f )
			{
				throw new ArgumentException( "Weights must all be >= 0." );
			}

			value -= item.Weight;

			if ( value <= 0f )
			{
				return item;
			}
		}

		throw new Exception( "We should have returned an item already!" );
	}
}
