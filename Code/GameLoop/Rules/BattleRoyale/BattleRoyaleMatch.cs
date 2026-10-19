using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A battle royale match, Warzone style: everyone for themselves, players and bots alike, with no respawns, inside a
/// closing zone (<see cref="SafeZoneManager"/>). The last one standing wins. It drops the players and bots in spread out
/// over the first circle (<see cref="BattleRoyaleDeploy"/>), starts the zone (<see cref="BattleRoyaleFight"/>), and keeps
/// the count of who's left, each player's placing and the winner for the HUD and the end screen.
/// </summary>
[Title( "Battle Royale Match" ), Icon( "emoji_events" )]
public sealed class BattleRoyaleMatch : Component, IGameEventHandler<KillEvent>
{
	public static BattleRoyaleMatch Current { get; private set; }

	/// <summary> How many bots drop in with the players, unless <c>br_bots</c> says otherwise (the hub sets it). </summary>
	[Property] public int BotCount { get; set; } = 40;

	/// <summary> Bots in the next battle royale; 0 uses the mode's own <see cref="BotCount"/>. </summary>
	[ConVar( "br_bots", Saved = true )] public static int BotCountSetting { get; set; }

	/// <summary> The next battle royale's map, by its scene's path; empty is the first of <see cref="GetMaps"/> (the hub sets it). </summary>
	[ConVar( "br_map", Saved = true )] public static string MapSetting { get; set; }

	public const int MaxBots = 100;

	public const string ModePrefab = "prefabs/game_modes/battle_royale.prefab";

	/// <summary>
	/// The maps battle royale is played on: Flatgrass, a match map that leaves the mode out of its list so it stays out
	/// of the usual map pickers, then every scene that lists the mode in its GameModes (Ridgeback).
	/// </summary>
	public static List<SceneFile> GetMaps()
	{
		var maps = GameUtils.GetMatchMaps()
			.Where( m => m.ResourcePath?.Contains( "flatgrass", StringComparison.OrdinalIgnoreCase ) ?? false )
			.ToList();

		foreach ( var scene in ResourceLibrary.GetAll<SceneFile>().OrderBy( s => s.ResourcePath ) )
		{
			if ( !maps.Contains( scene ) && scene.GetMetadata( "GameModes", "" ).Contains( ModePrefab, StringComparison.OrdinalIgnoreCase ) )
				maps.Add( scene );
		}

		return maps;
	}

	/// <summary> The map picked for the next battle royale (<c>br_map</c>), else the first there is. </summary>
	public static SceneFile GetChosenMap()
	{
		var maps = GetMaps();
		return maps.FirstOrDefault( m => string.Equals( m.ResourcePath, MapSetting, StringComparison.OrdinalIgnoreCase ) )
			?? maps.FirstOrDefault();
	}

	/// <summary> Where the match goes once it has a winner. </summary>
	[Property] public StateComponent MatchEndedState { get; set; }

	/// <summary>
	/// With every real player out, the bots could take minutes to settle it, so the match ends this long after the last
	/// player falls (time for the deathcam).
	/// </summary>
	[Property] public float EndAfterPlayersOut { get; set; } = 8f;

	/// <summary> How far apart everyone lands, where there's room. </summary>
	[Property] public float DropSpacing { get; set; } = 1800f;

	/// <summary> Bots spawned per tick while dropping in, so a hundred don't all land in one frame. </summary>
	private const int SpawnsPerTick = 3;

	[Sync( SyncFlags.FromHost )] public bool IsRunning { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsOver { get; private set; }
	[Sync( SyncFlags.FromHost )] public int AliveCount { get; private set; }
	[Sync( SyncFlags.FromHost )] public int StartCount { get; private set; }
	[Sync( SyncFlags.FromHost )] public string WinnerName { get; private set; }
	/// <summary> The winning player's Client object, or empty when a bot won or nobody did. </summary>
	[Sync( SyncFlags.FromHost )] public Guid WinnerClientId { get; private set; }
	/// <summary> Each player's placing once they're out (or have won), by their Client object's id: 12 is twelfth. </summary>
	[Sync( SyncFlags.FromHost )] public NetDictionary<Guid, int> Placements { get; set; } = new();

	/// <summary> The local player's placing, or 0 while they're still in (or never were). </summary>
	public int LocalPlacement => Client.Local.IsValid() && Placements.TryGetValue( Client.Local.GameObject.Id, out var place ) ? place : 0;

	/// <summary> Did the local player win? </summary>
	public bool LocalPlayerWon => IsOver && Client.Local.IsValid() && WinnerClientId == Client.Local.GameObject.Id;

	private int _botsToSpawn;
	private readonly List<Vector3> _dropPoints = new();
	private bool _playersJoined;
	private TimeSince _timeSinceStart;
	private TimeSince _timeSincePlayersOut;
	private bool _playersOut;
	private string _lastToFall;

	protected override void OnEnabled()
	{
		Current = this;
	}

	protected override void OnDisabled()
	{
		if ( Current == this )
			Current = null;
	}

	#region Drop in

	/// <summary>
	/// Host: the first circle: the map's <see cref="BattleRoyaleArea"/> if it has one (Ridgeback), else taking in the whole
	/// navmesh (Flatgrass's is about 32000 units across). Sampled rather than read from the navmesh's bounds, which cover
	/// the whole map's geometry. Not while the navmesh is still being built, which on a big map can outlast the scene's
	/// loading: the circle comes once it's done.
	/// </summary>
	public void EnsureFirstCircle()
	{
		var zone = SafeZoneManager.Current;
		if ( zone is null || zone.HasCircle || Scene.NavMesh.IsGenerating )
			return;

		if ( Scene.GetAllComponents<BattleRoyaleArea>().FirstOrDefault() is { } area )
		{
			var middle = area.WorldPosition;
			zone.SetFirstCircle( Scene.NavMesh.GetClosestPoint( middle, 4000f ) ?? middle, area.Radius );
			return;
		}

		var points = new List<Vector3>();
		for ( var i = 0; i < 96; i++ )
		{
			if ( Scene.NavMesh.GetRandomPoint() is { } point )
				points.Add( point );
		}

		if ( points.Count == 0 )
		{
			zone.SetFirstCircle( Vector3.Zero, 8000f );
			return;
		}

		var box = BBox.FromPoints( points );
		var center = box.Center;
		var radius = 0f;
		foreach ( var point in points )
			radius = MathF.Max( radius, point.WithZ( 0f ).Distance( center.WithZ( 0f ) ) );

		center = Scene.NavMesh.GetClosestPoint( center, 4000f ) ?? center;
		zone.SetFirstCircle( center, MathF.Max( radius, 2000f ) );
	}

	/// <summary> Host: set up the first circle and start dropping the bots in (the Preparing state). </summary>
	public void Deploy()
	{
		EnsureFirstCircle();
		IsRunning = false;
		IsOver = false;
		WinnerName = null;
		WinnerClientId = Guid.Empty;
		Placements.Clear();
		_botsToSpawn = Math.Clamp( BotCountSetting > 0 ? BotCountSetting : BotCount, 0, MaxBots );
	}

	/// <summary>
	/// Host: somewhere to land, spread out over the first circle away from everyone already down, on ground a bot can
	/// walk from (not Flatgrass's roof).
	/// </summary>
	public bool TryGetDropPoint( out Vector3 position )
	{
		EnsureFirstCircle();
		position = default;
		var zone = SafeZoneManager.Current;
		var bots = LightweightBotManager.Instance;
		if ( zone is null || !zone.HasCircle )
			return false;

		// Wherever there's room: the spacing gives way if the map's crowded.
		for ( var spacing = DropSpacing; spacing >= 200f; spacing *= 0.5f )
		{
			for ( var i = 0; i < 12; i++ )
			{
				if ( Scene.NavMesh.GetRandomPoint( zone.ZoneCenter, zone.CurrentRadius * 0.9f ) is not { } point )
					continue;
				if ( !IsClear( point, spacing ) )
					continue;
				if ( bots.IsValid() && !bots.IsWalkable( point ) )
					continue;

				_dropPoints.Add( point );
				position = point;
				return true;
			}
		}

		return false;
	}

	private bool IsClear( Vector3 point, float spacing )
	{
		var spacingSquared = spacing * spacing;
		foreach ( var other in _dropPoints )
		{
			if ( other.DistanceSquared( point ) < spacingSquared )
				return false;
		}

		foreach ( var pawn in GameUtils.PlayerPawns )
		{
			if ( pawn.WorldPosition.DistanceSquared( point ) < spacingSquared )
				return false;
		}

		return true;
	}

	private void SpawnSomeBots()
	{
		if ( _botsToSpawn <= 0 )
			return;

		// Nowhere to land until the navmesh is built: they drop in when it is.
		if ( Scene.NavMesh.IsGenerating )
			return;

		var manager = GetBotManager();
		if ( !manager.IsValid() )
		{
			_botsToSpawn = 0;
			return;
		}

		for ( var i = 0; i < SpawnsPerTick && _botsToSpawn > 0; i++ )
		{
			_botsToSpawn--;
			if ( !TryGetDropPoint( out var point ) )
				continue;

			manager.SpawnBot( Team.Unassigned, new Transform( point, Rotation.FromYaw( Game.Random.Float( 0f, 360f ) ) ) );
		}
	}

	private LightweightBotManager GetBotManager()
	{
		var manager = LightweightBotManager.Instance;
		if ( manager.IsValid() )
			return manager;

		manager = Scene.GetAllComponents<LightweightBotManager>().FirstOrDefault();
		if ( manager.IsValid() )
			return manager;

		var obj = new GameObject( true, "Lightweight Bot Manager" );
		obj.Flags |= GameObjectFlags.NotSaved;
		manager = obj.AddComponent<LightweightBotManager>();
		if ( Networking.IsActive )
			obj.NetworkSpawn( true, null );

		return manager;
	}

	#endregion

	#region Fight

	/// <summary> Host: the fight is on (the Play Game state): the zone starts its first hold. </summary>
	public void StartFight()
	{
		IsRunning = true;
		IsOver = false;
		_timeSinceStart = 0f;
		_playersOut = false;
		_playersJoined = false;
		_lastToFall = null;
		CountAlive( out var alive, out _, out _ );
		StartCount = alive + _botsToSpawn;
		AliveCount = alive;
		StartZone();
	}

	/// <summary> Host: the zone starts its first hold, as soon as there's a first circle (see <see cref="EnsureFirstCircle"/>). </summary>
	private void StartZone()
	{
		EnsureFirstCircle();
		if ( SafeZoneManager.Current is { IsRunning: false, HasCircle: true } zone )
			zone.StartClosing();
	}

	private readonly List<Client> _clientScratch = new();
	private readonly List<PlayerPawn> _pawnScratch = new();
	private readonly List<LightweightCombatBot> _botScratch = new();
	private readonly HashSet<PlayerPawn> _countedPawns = new();

	/// <summary>
	/// Who's still in. It runs every fixed tick, so it searches the scene as <see cref="GameUtils.PlayerPawns"/> and
	/// <see cref="GameUtils.LightweightBots"/> do (every client's pawn and every pawn in the scene, each once; every bot),
	/// into lists kept for it rather than through their allocations. Not BotSystem's frame lists: bots dropped in this tick
	/// have to count.
	/// </summary>
	private void CountAlive( out int alive, out int playersAlive, out Component last )
	{
		alive = 0;
		playersAlive = 0;
		last = null;

		_countedPawns.Clear();
		_clientScratch.Clear();
		Scene.GetAll( _clientScratch );
		foreach ( var client in _clientScratch )
			CountPawn( client.PlayerPawn, ref alive, ref playersAlive, ref last );

		_pawnScratch.Clear();
		Scene.GetAll( _pawnScratch );
		foreach ( var pawn in _pawnScratch )
			CountPawn( pawn, ref alive, ref playersAlive, ref last );

		_botScratch.Clear();
		Scene.GetAll( _botScratch );
		foreach ( var bot in _botScratch )
		{
			if ( !bot.IsValid() || !bot.IsAlive )
				continue;

			alive++;
			last = bot;
		}
	}

	private void CountPawn( PlayerPawn pawn, ref int alive, ref int playersAlive, ref Component last )
	{
		if ( !pawn.IsValid() || !_countedPawns.Add( pawn ) )
			return;
		if ( !pawn.HealthComponent.IsValid() || pawn.HealthComponent.State != LifeState.Alive )
			return;
		if ( pawn.Client.IsValid() && pawn.Client.IsBot )
			return;

		alive++;
		playersAlive++;
		last = pawn;
	}

	protected override void OnFixedUpdate()
	{
		if ( !Networking.IsHost )
			return;

		SpawnSomeBots();

		if ( !IsRunning || IsOver )
			return;

		StartZone();

		CountAlive( out var alive, out var playersAlive, out var last );
		AliveCount = alive;
		StartCount = Math.Max( StartCount, alive );
		_playersJoined |= playersAlive > 0;

		// A moment's grace while the last bots land.
		if ( _timeSinceStart < 3f || _botsToSpawn > 0 )
			return;

		if ( alive <= 1 )
		{
			EndMatch( last );
			return;
		}

		if ( _playersJoined && playersAlive == 0 )
		{
			if ( !_playersOut )
			{
				_playersOut = true;
				_timeSincePlayersOut = 0f;
			}
			else if ( _timeSincePlayersOut > EndAfterPlayersOut )
			{
				EndMatch( null );
			}
		}
	}

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs ) => OnKill( eventArgs.DamageInfo );

	private void OnKill( DamageInfo damageInfo )
	{
		if ( !Networking.IsHost || !IsRunning || IsOver )
			return;

		var victim = (Component)GameUtils.GetPlayerFromComponent( damageInfo.Victim ) ?? GameUtils.GetLightweightBotFromComponent( damageInfo.Victim );
		if ( !victim.IsValid() )
			return;

		_lastToFall = NameOf( victim );

		// Everyone still standing, plus this one: they placed just behind them all.
		CountAlive( out var alive, out _, out _ );
		AliveCount = alive;
		if ( victim is PlayerPawn { Client: { IsValid: true, IsBot: false } client } )
			Placements[client.GameObject.Id] = alive + 1;
	}

	private void EndMatch( Component winner )
	{
		IsOver = true;
		IsRunning = false;
		SafeZoneManager.Current?.Stop();

		WinnerName = winner.IsValid() ? NameOf( winner ) : _playersOut ? null : _lastToFall;
		WinnerClientId = winner is PlayerPawn { Client: { IsValid: true } client } ? client.GameObject.Id : Guid.Empty;
		if ( WinnerClientId != Guid.Empty )
			Placements[WinnerClientId] = 1;

		if ( !string.IsNullOrEmpty( WinnerName ) )
			GameMode.Instance?.ShowToast( $"{WinnerName} Wins!", duration: 6f );

		if ( MatchEndedState.IsValid() )
			GameMode.Instance?.StateMachine.Transition( MatchEndedState );
	}

	private static string NameOf( Component combatant ) => combatant switch
	{
		PlayerPawn { Client: { IsValid: true } client } => client.DisplayName,
		IDescription description => description.DisplayName,
		_ => "Someone"
	};

	#endregion
}

/// <summary> Battle royale: when this state starts (Preparing), set up the first zone and drop the bots in. </summary>
[Title( "Battle Royale Deploy" ), Icon( "paragliding" )]
public sealed class BattleRoyaleDeploy : Component, IGameEventHandler<EnterStateEvent>
{
	void IGameEventHandler<EnterStateEvent>.OnGameEvent( EnterStateEvent eventArgs ) => Deploy();

	private void Deploy()
	{
		if ( Networking.IsHost )
			BattleRoyaleMatch.Current?.Deploy();
	}
}

/// <summary> Battle royale: when this state starts (Play Game), the fight is on and the zone starts closing. </summary>
[Title( "Battle Royale Fight" ), Icon( "sports_mma" )]
public sealed class BattleRoyaleFight : Component, IGameEventHandler<EnterStateEvent>
{
	void IGameEventHandler<EnterStateEvent>.OnGameEvent( EnterStateEvent eventArgs ) => StartFight();

	private void StartFight()
	{
		if ( Networking.IsHost )
			BattleRoyaleMatch.Current?.StartFight();
	}
}

/// <summary>
/// Battle royale spawns: spread out over the first circle, away from everyone already down
/// (<see cref="BattleRoyaleMatch.TryGetDropPoint"/>), instead of the map's spawn points (Flatgrass's are all on its roof).
/// </summary>
[Title( "Battle Royale Spawn Assigner" ), Icon( "place" )]
public sealed class BattleRoyaleSpawnAssigner : Component, ISpawnAssigner
{
	public SpawnPointInfo GetSpawnPoint( Client player )
	{
		var rotation = Rotation.FromYaw( Game.Random.Float( 0f, 360f ) );
		if ( BattleRoyaleMatch.Current is { } match && match.TryGetDropPoint( out var point ) )
			return new SpawnPointInfo( new Transform( point, rotation ), Array.Empty<string>() );

		return Random.Shared.FromArray( GameUtils.GetSpawnPoints().ToArray(),
			new SpawnPointInfo( global::Transform.Zero, Array.Empty<string>() ) );
	}
}
