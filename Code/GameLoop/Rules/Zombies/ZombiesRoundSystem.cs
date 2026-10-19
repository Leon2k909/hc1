using Sandbox;
using System;

namespace Facepunch;

/// <summary>
/// Drives a CoD-style zombies game: rounds, zombie spawning and scaling, power-ups,
/// buy stations, holding dead players until the next round, and game over / restart.
/// </summary>
public sealed class ZombiesRoundSystem : Component
{
	public static ZombiesRoundSystem Current { get; private set; }

	[Property, Sync( SyncFlags.FromHost )] public int CurrentRound { get; private set; } = 0;
	[Property, Sync( SyncFlags.FromHost )] public int ZombiesRemainingInRound { get; private set; } = 0;
	[Property, Sync( SyncFlags.FromHost )] public int ZombiesAlive { get; private set; } = 0;
	[Property, Sync( SyncFlags.FromHost )] public float TimeBetweenRounds { get; set; } = 10f;
	[Property, Sync( SyncFlags.FromHost )] public bool IsIntermission { get; private set; } = true;
	[Sync( SyncFlags.FromHost )] public bool IsGameOver { get; private set; }
	[Sync( SyncFlags.FromHost ), Change( nameof( OnPauseStateChanged ) )] public bool IsPaused { get; private set; }
	[Sync( SyncFlags.FromHost )] public int GameOverRound { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeUntil TimeUntilNextRound { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeUntil TimeUntilRestart { get; private set; }

	/// <summary>Opening cinematic: plays once when the first player arrives, and again after a restart.</summary>
	[Sync( SyncFlags.FromHost )] public bool IntroPlaying { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeSince TimeSinceIntro { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeSince TimeSinceRoundStart { get; private set; }
	public const float IntroDuration = 9f;

	[Sync( SyncFlags.FromHost )] public TimeUntil OneHitKillsTime { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeUntil PointBoostTime { get; private set; }

	[Property] public GameObject ZombiePrefab { get; set; }
	[Property] public Model ZombieBodyModel { get; set; }
	[Property] public Model WeaponCrateModel { get; set; }

	/// <summary>Killed zombies can drop power-ups (Resupply, One-Hit Kills, Point Boost, Clean Sweep). Off for now.</summary>
	[Property] public bool DropPowerUps { get; set; } = false;

	public const float PowerUpDuration = 30f;
	public const float GameOverDuration = 12f;
	public const int MaxPowerUpsPerRound = 4;

	private TimeSince _lastSpawnTime;
	private int _powerUpsThisRound;
	private bool _stationsPlaced;
	private bool _anyoneSpawned;
	private readonly HashSet<Client> _heldClients = new();
	private bool _pauseTimeScaleApplied;
	private float _timeScaleBeforePause = 1f;

	protected override void OnAwake() => Current = this;

	protected override void OnDestroy()
	{
		if ( _pauseTimeScaleApplied )
			Scene.TimeScale = _timeScaleBeforePause > 0f ? _timeScaleBeforePause : 1f;

		if ( Current == this ) Current = null;
	}

	protected override void OnStart()
	{
		Current = this;
		if ( !_pauseTimeScaleApplied )
			_timeScaleBeforePause = Scene.TimeScale;
		if ( !Networking.IsHost ) return;

		OneHitKillsTime = 0;
		PointBoostTime = 0;
		// Wait for the first player; the intro then counts down to round 1.
		BeginIntermission( 9999f );
	}

	/// <summary>
	/// Pause or resume the Zombies match from the pause menu. Only a player on their own pauses it: the pause is the
	/// whole scene's time, so with others in the match, whoever opened the menu froze everyone where they stood.
	/// </summary>
	public void SetPausedFromMenu( bool paused )
	{
		if ( !Networking.IsHost )
		{
			HostSetPausedFromMenu( paused );
			return;
		}

		ApplyMenuPause( paused );
	}

	[Rpc.Host]
	private void HostSetPausedFromMenu( bool paused ) => ApplyMenuPause( paused );

	private void ApplyMenuPause( bool paused )
	{
		IsPaused = paused && CountHumanPlayers() <= 1;
		ApplyPauseTimeScale();
	}

	// ── Queries ─────────────────────────────────────────────────────────────────
	public bool IsPowerUpActive( ZombiesPowerUpType type ) => type switch
	{
		ZombiesPowerUpType.OneHitKills => OneHitKillsTime > 0,
		ZombiesPowerUpType.PointBoost => PointBoostTime > 0,
		_ => false
	};

	/// <summary>Real players (not bots) who currently have a pawn in the game.</summary>
	private static IEnumerable<PlayerPawn> HumanPawns( Scene scene ) => scene.GetAllComponents<PlayerPawn>()
		.Where( p => p.IsValid() && p.Client.IsValid() && !p.Client.IsBot );

	/// <summary>Players who are alive and on their feet (or about to be, via solo Second Wind).</summary>
	public static int CountActivePlayers()
	{
		var scene = Game.ActiveScene;
		if ( scene is null ) return 0;
		return HumanPawns( scene ).Count( IsActivePlayer );
	}

	/// <summary><see cref="CountActivePlayers()"/> among <paramref name="humanPawns"/>, without searching the scene.</summary>
	private static int CountActivePlayers( List<PlayerPawn> humanPawns )
	{
		var count = 0;
		foreach ( var pawn in humanPawns )
		{
			if ( IsActivePlayer( pawn ) )
				count++;
		}

		return count;
	}

	private static bool IsActivePlayer( PlayerPawn p ) => p.HealthComponent.State == LifeState.Alive
		&& ZombiesPlayerState.For( p ) is not { IsDowned: true, IsSelfReviving: false };

	/// <summary>The real players' pawns, taken once an update for the checks the host makes every frame.</summary>
	private readonly List<PlayerPawn> _humanPawns = new();
	private readonly List<PlayerPawn> _pawnScratch = new();
	private readonly List<LightweightCombatBot> _botScratch = new();

	private void RefreshHumanPawns()
	{
		_pawnScratch.Clear();
		Scene.GetAll( _pawnScratch );
		_humanPawns.Clear();
		foreach ( var p in _pawnScratch )
		{
			if ( p.IsValid() && p.Client.IsValid() && !p.Client.IsBot )
				_humanPawns.Add( p );
		}
	}

	/// <summary>Real players in the game, whatever state they're in.</summary>
	public static int CountHumanPlayers() => GameUtils.AllPlayers.Count( c => c.IsConnected && !c.IsBot );

	/// <summary>The box's guns, which the wall-buys are also picked from. WIP guns are left out of both.</summary>
	public static IEnumerable<EquipmentResource> GetWeaponCratePool() => ResourceLibrary.GetAll<EquipmentResource>()
		.Where( x => (x.Slot == EquipmentSlot.Primary || x.Slot == EquipmentSlot.Secondary) && !x.IsWip
			&& x.ViewModelPrefab.IsValid() && x.MainPrefab.IsValid()
			&& !Gunsmith.GunsmithLoadoutManager.IsMergedWeaponResource( x ) );

	/// <summary>Held players wait out the round dead, CoD-style, and come back at the next one.</summary>
	public bool ShouldHoldRespawn( Client client ) => client.IsValid() && _heldClients.Contains( client );

	// ── Round flow ──────────────────────────────────────────────────────────────
	protected override void OnUpdate()
	{
		ApplyPauseTimeScale();
		if ( !Networking.IsHost ) return;

		// Someone joined a match paused on its own: play on.
		if ( IsPaused && CountHumanPlayers() > 1 )
			ApplyMenuPause( false );

		RemoveCombatBots();
		RefreshHumanPawns();
		TrackDeadPlayers();

		if ( IntroPlaying && TimeSinceIntro > IntroDuration + 1f )
			IntroPlaying = false;

		if ( !_stationsPlaced && _anyoneSpawned )
		{
			PlayIntro();
			PlaceBuyStations();
			_stationsPlaced = true;
		}

		if ( IsGameOver )
		{
			if ( TimeUntilRestart <= 0 ) RestartGame();
			return;
		}

		if ( _anyoneSpawned && CountActivePlayers( _humanPawns ) == 0 && GameUtils.AllPlayers.Any( c => c.IsConnected && !c.IsBot ) )
		{
			GameOver();
			return;
		}

		if ( IsIntermission )
		{
			if ( TimeUntilNextRound <= 0 ) StartNextRound();
			return;
		}

		if ( ZombiesRemainingInRound > 0 && ZombiesAlive < GetMaxZombiesAllowed( Math.Max( 1, _humanPawns.Count ) ) && _lastSpawnTime > GetSpawnRate() )
			SpawnZombie();

		if ( ZombiesRemainingInRound <= 0 && ZombiesAlive <= 0 )
			EndRound();
	}

	private void OnPauseStateChanged( bool oldValue, bool newValue ) => ApplyPauseTimeScale();

	private void ApplyPauseTimeScale()
	{
		if ( IsPaused )
		{
			if ( !_pauseTimeScaleApplied )
				_timeScaleBeforePause = Scene.TimeScale;

			Scene.TimeScale = 0f;
			_pauseTimeScaleApplied = true;
		}
		else if ( _pauseTimeScaleApplied )
		{
			Scene.TimeScale = _timeScaleBeforePause > 0f ? _timeScaleBeforePause : 1f;
			_pauseTimeScaleApplied = false;
		}
	}

	private void TrackDeadPlayers()
	{
		foreach ( var pawn in _humanPawns )
		{
			_anyoneSpawned = true;
			if ( pawn.HealthComponent.State == LifeState.Dead )
				_heldClients.Add( pawn.Client );
		}
	}

	private int PlayerCount => Math.Max( 1, HumanPawns( Scene ).Count() );

	private void StartNextRound()
	{
		CurrentRound++;
		IsIntermission = false;
		TimeSinceRoundStart = 0;
		_powerUpsThisRound = 0;

		var r = CurrentRound;
		var baseCount = 5 + 3 * r + r * r * 0.15f;
		ZombiesRemainingInRound = (int)(baseCount * (1f + 0.5f * (PlayerCount - 1)));

		Log.Info( $"[Zombies] Round {CurrentRound}: {ZombiesRemainingInRound} zombies." );
	}

	private void EndRound()
	{
		BroadcastSound( "sounds/ui/countdown/countdown_activate.sound" );
		Log.Info( $"[Zombies] Round {CurrentRound} cleared." );
		BeginIntermission( TimeBetweenRounds );
	}

	private void BeginIntermission( float seconds )
	{
		IsIntermission = true;
		TimeUntilNextRound = seconds;

		// Everyone back on their feet, and the dead come back for the next round.
		foreach ( var pawn in HumanPawns( Scene ) )
		{
			ZombiesPlayerState.For( pawn )?.ForceRevive();
			if ( pawn.HealthComponent.State == LifeState.Alive )
				pawn.HealthComponent.Health = pawn.HealthComponent.MaxHealth;
		}

		foreach ( var client in _heldClients )
		{
			if ( client.IsValid() ) client.RespawnState = RespawnState.Immediate;
		}
		_heldClients.Clear();
	}

	private void GameOver()
	{
		IsGameOver = true;
		GameOverRound = CurrentRound;
		TimeUntilRestart = GameOverDuration;
		BroadcastSound( "sounds/ui/countdown/countdown_activate.sound" );
		Log.Info( $"[Zombies] Game over on round {CurrentRound}." );

		foreach ( var z in Scene.GetAllComponents<ZombieAI>().ToList() )
			z.GameObject.Destroy();
	}

	private void RestartGame()
	{
		foreach ( var z in Scene.GetAllComponents<ZombieAI>().ToList() ) z.GameObject.Destroy();
		foreach ( var p in Scene.GetAllComponents<ZombiesPowerUp>().ToList() ) p.GameObject.Destroy();

		IsGameOver = false;
		CurrentRound = 0;
		ZombiesAlive = 0;
		ZombiesRemainingInRound = 0;
		OneHitKillsTime = 0;
		PointBoostTime = 0;
		_heldClients.Clear();

		// Fresh pawns give everyone their starting loadout back.
		foreach ( var client in GameUtils.AllPlayers.Where( c => c.IsConnected && !c.IsBot ).ToList() )
			client.Respawn( true );

		// Old pawns saved their points and kills as they were destroyed; a new game starts from scratch.
		ZombiesGameMode.CarriedPoints.Clear();
		ZombiesGameMode.CarriedKills.Clear();
		foreach ( var eco in Scene.GetAllComponents<ZombiesPlayerEconomy>() )
			eco.ResetEconomy();

		BeginIntermission( 5f );
		PlayIntro();
	}

	private void PlayIntro()
	{
		IntroPlaying = true;
		TimeSinceIntro = 0;
		// Round 1 begins as the intro finishes.
		BeginIntermission( IntroDuration );
	}

	/// <summary>Called by <see cref="ZombiesGameMode"/> for every new pawn.</summary>
	public void OnPlayerSpawned( PlayerPawn pawn )
	{
		if ( pawn.Client.IsValid() ) _heldClients.Remove( pawn.Client );
	}

	public void OnPlayerDowned( ZombiesPlayerState state )
	{
		using ( Rpc.FilterInclude( c => c != state.Network.Owner ) )
		{
			GameMode.Instance?.ShowToast( $"{state.Player?.DisplayName} is down! Hold E on them to revive", Facepunch.UI.ToastType.Generic, 4 );
		}
	}

	/// <summary>Play a 2D sound for everyone (host-side Sound.Play only plays on the host).</summary>
	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void BroadcastSound( string sound )
	{
		Sound.Play( sound );
	}

	// ── Spawning ────────────────────────────────────────────────────────────────
	/// <summary>Zombie health: CoD-shaped curve, scaled down for this game's weapon damage.</summary>
	public static float GetZombieHealth( int round )
	{
		if ( round <= 9 ) return 100f + 60f * (round - 1);
		return (100f + 60f * 8) * MathF.Pow( 1.1f, round - 9 );
	}

	private ZombieSpeed RollSpeed()
	{
		var r = CurrentRound;

		// The last zombie of the round always runs, so rounds don't drag.
		if ( ZombiesRemainingInRound <= 1 && r >= 2 ) return ZombieSpeed.Sprint;

		var sprintChance = r >= 6 ? Math.Min( 0.8f, (r - 5) * 0.15f ) : 0f;
		var jogChance = r >= 3 ? Math.Min( 1f, (r - 2) * 0.25f ) : 0f;
		var roll = Game.Random.Float();
		if ( roll < sprintChance ) return ZombieSpeed.Sprint;
		if ( roll < sprintChance + jogChance ) return ZombieSpeed.Jog;
		return ZombieSpeed.Walk;
	}

	private int GetMaxZombiesAllowed( int playerCount ) => Math.Min( 24 + 6 * (playerCount - 1), 10 + CurrentRound * 2 );

	private float GetSpawnRate() => Math.Max( 0.4f, 2.0f - CurrentRound * 0.1f );

	private bool TryFindSpawnPosition( out Vector3 position )
	{
		position = default;

		var targets = HumanPawns( Scene ).Where( p => p.HealthComponent.State == LifeState.Alive ).ToList();
		if ( targets.Count == 0 ) return false;

		float NearestPlayer( Vector3 pos ) => targets.Min( p => p.WorldPosition.Distance( pos ) );
		bool CanReachAnyone( Vector3 pos ) => targets.Any( p => CanWalk( pos, p.WorldPosition, 3000f ) );

		// A Zombies map's own spawn points come first (ZombieSpawnPoint): a fence gap or the woods' edge, out of sight
		// and neither in the players' faces nor across the map. One in sight is only a fallback.
		var zombiePoints = Scene.GetAllComponents<ZombieSpawnPoint>()
			.Select( x => x.WorldPosition )
			.Where( p => { var d = NearestPlayer( p ); return d > 600f && d < 3200f; } )
			.OrderBy( _ => Game.Random.Float() )
			.Take( 6 )
			.ToList();
		Vector3? seenPoint = null;
		foreach ( var p in zombiePoints )
		{
			if ( !CanReachAnyone( p ) ) continue;
			if ( targets.Any( x => CanSee( x, p ) ) )
			{
				seenPoint ??= p;
				continue;
			}

			position = p;
			return true;
		}

		if ( seenPoint.HasValue )
		{
			position = seenPoint.Value;
			return true;
		}

		// Prefer map spawn points that are out of the players' faces but not miles away.
		if ( MapSpawnSettings.MapSpawnPointsAllowed )
		{
			var points = Scene.GetAllComponents<SpawnPoint>()
				.Select( x => x.WorldPosition )
				.Where( p => { var d = NearestPlayer( p ); return d > 700f && d < 2600f; } )
				.OrderBy( _ => Game.Random.Float() )
				.Take( 4 );

			foreach ( var p in points )
			{
				if ( !CanReachAnyone( p ) ) continue;
				position = p;
				return true;
			}
		}

		// Otherwise pick a navmesh point around a random player. Maps like Innocent Hotel have navmesh islands
		// nobody can walk to (its basement and roof), so the zombie has to be able to reach someone. Indoors,
		// prefer spots round a corner: popping up in plain sight looks wrong, so those are only a fallback.
		Vector3? seen = null;
		for ( int i = 0; i < 16; i++ )
		{
			var target = targets[Game.Random.Int( 0, targets.Count - 1 )];
			var nav = i % 2 == 0
				? Scene.NavMesh.GetClosestPoint( target.WorldPosition + Vector3.Random.WithZ( 0 ).Normal * Game.Random.Float( 900f, 1500f ), 400f )
				: Scene.NavMesh.GetRandomPoint( target.WorldPosition, 1500f );
			if ( nav is not { } p ) continue;

			var visible = targets.Any( x => CanSee( x, p ) );
			if ( NearestPlayer( p ) < (visible ? 700f : 450f) ) continue;
			if ( visible && seen.HasValue ) continue;
			if ( !CanReachAnyone( p ) ) continue;

			if ( visible )
			{
				seen = p;
				continue;
			}

			position = p;
			return true;
		}

		position = seen.GetValueOrDefault();
		return seen.HasValue;
	}

	/// <summary>Can <paramref name="player"/> see a zombie standing at <paramref name="position"/>?</summary>
	private bool CanSee( PlayerPawn player, Vector3 position )
	{
		var eye = player.WorldPosition + Vector3.Up * 64f;
		return !Scene.Trace.Ray( eye, position + Vector3.Up * 48f )
			.WithoutTags( "player", "enemy", "trigger" )
			.Run().Hit;
	}

	/// <summary>
	/// Is there a navmesh path from <paramref name="from"/> to <paramref name="to"/> no longer than <paramref name="maxLength"/>?
	/// </summary>
	private bool CanWalk( Vector3 from, Vector3 to, float maxLength )
	{
		var end = Scene.NavMesh.GetClosestPoint( to, 200f ) ?? to;
		var path = Scene.NavMesh.CalculatePath( new Sandbox.Navigation.CalculatePathRequest { Start = from, Target = end } );
		if ( path.Status != Sandbox.Navigation.NavMeshPathStatus.Complete || path.Points is null ) return false;

		var length = 0f;
		var previous = from;
		foreach ( var point in path.Points )
		{
			length += previous.Distance( point.Position );
			previous = point.Position;
		}

		return length <= maxLength;
	}

	/// <summary>Zombies is co-op against zombies only: clear out any deathmatch combat bots.</summary>
	private void RemoveCombatBots()
	{
		_botScratch.Clear();
		Scene.GetAll( _botScratch );
		foreach ( var bot in _botScratch )
			bot.GameObject.Destroy();
	}

	private void SpawnZombie()
	{
		_lastSpawnTime = 0;

		if ( !TryFindSpawnPosition( out var pos ) ) return;

		GameObject zombie;

		if ( ZombiePrefab.IsValid() )
		{
			zombie = ZombiePrefab.Clone( pos );
		}
		else
		{
			zombie = new GameObject( true, "Zombie" );
			zombie.WorldPosition = pos;
			zombie.Tags.Add( "enemy" );

			// The zombie model has no animations of its own, but shares the citizen_human skeleton:
			// an invisible animated human drives it through bone merge. The driver plays zombie clips as
			// sequences; if it's missing, fall back to the citizen and its (human) animgraph.
			var renderer = zombie.Components.Create<SkinnedModelRenderer>();
			var driver = Model.Load( ZombieAI.DriverModel );
			renderer.UseAnimGraph = driver is null || driver.IsError;
			renderer.Model = renderer.UseAnimGraph ? Model.Load( ZombieAI.CitizenModel ) : driver;
			if ( ZombieBodyModel is { IsError: false } )
			{
				renderer.RenderType = ModelRenderer.ShadowRenderType.Off;
				renderer.RenderOptions.Game = false;
				var bodyGo = new GameObject( zombie, true, "Body" );
				var body = bodyGo.Components.Create<SkinnedModelRenderer>();
				body.Model = ZombieBodyModel;
				body.BoneMergeTarget = renderer;
			}
			else
			{
				// Keep enemies visible and animated if a custom model is unavailable.
				renderer.Tint = new Color( 0.45f, 0.6f, 0.35f );
			}

			// The capsule below stops bullets, but it stands well clear of the arms, legs and chest. A bullet's blood
			// goes where it meets the driver's hitboxes, the body's own shape (SceneTraceExtensions.ThroughBody). Only traces
			// that ask for hitboxes see them, so they don't change how zombies move or block.
			var hitboxes = zombie.Components.Create<ModelHitboxes>();
			hitboxes.Renderer = renderer;

			var nav = zombie.Components.Create<NavMeshAgent>();
			nav.Height = 72f;
			nav.Radius = 16f;

			var collider = zombie.Components.Create<CapsuleCollider>();
			collider.Radius = 16f;
			collider.Start = new Vector3( 0, 0, 16f );
			collider.End = new Vector3( 0, 0, 72f );

			zombie.Components.Create<ZombieAI>();
		}

		if ( zombie.Components.TryGet<ZombieAI>( out var ai ) )
		{
			ai.MaxHealth = GetZombieHealth( CurrentRound );
			ai.Speed = RollSpeed();
		}

		zombie.NetworkSpawn( null );

		ZombiesRemainingInRound--;
		ZombiesAlive++;
	}

	public void OnZombieKilled( Vector3 position )
	{
		if ( !Networking.IsHost ) return;
		ZombiesAlive = Math.Max( 0, ZombiesAlive - 1 );
		TryDropPowerUp( position );
	}

	/// <summary>A zombie that got lost or stuck far away is removed and re-queued.</summary>
	public void OnZombieRecycled()
	{
		if ( !Networking.IsHost ) return;
		ZombiesAlive = Math.Max( 0, ZombiesAlive - 1 );
		ZombiesRemainingInRound++;
	}

	// ── Power-ups ───────────────────────────────────────────────────────────────
	private void TryDropPowerUp( Vector3 position )
	{
		if ( !DropPowerUps ) return;
		if ( _powerUpsThisRound >= MaxPowerUpsPerRound ) return;
		if ( Game.Random.Float() > 0.03f ) return;

		_powerUpsThisRound++;
		var types = Enum.GetValues<ZombiesPowerUpType>();
		ZombiesPowerUp.Spawn( Scene, position, types[Game.Random.Int( 0, types.Length - 1 )] );
	}

	public void ActivatePowerUp( ZombiesPowerUpType type, PlayerPawn collector )
	{
		if ( !Networking.IsHost ) return;

		switch ( type )
		{
			case ZombiesPowerUpType.Resupply:
				foreach ( var pawn in HumanPawns( Scene ) )
					if ( pawn.HealthComponent.State == LifeState.Alive ) pawn.Inventory.RefillAmmo();
				break;

			case ZombiesPowerUpType.OneHitKills:
				OneHitKillsTime = PowerUpDuration;
				break;

			case ZombiesPowerUpType.PointBoost:
				PointBoostTime = PowerUpDuration;
				break;

			case ZombiesPowerUpType.CleanSweep:
				foreach ( var z in Scene.GetAllComponents<ZombieAI>().ToList() )
					z.Kill( null );
				foreach ( var pawn in HumanPawns( Scene ) )
					pawn.GetComponent<ZombiesPlayerEconomy>()?.AddPoints( 400 );
				break;
		}

		GameMode.Instance?.ShowToast( ZombiesPowerUp.GetName( type ).ToUpper(), Facepunch.UI.ToastType.Generic, 3 );
		BroadcastSound( "sounds/music/round_intro/round_start.sound" );
	}

	// ── Buy stations ────────────────────────────────────────────────────────────
	/// <summary>
	/// The zombies maps have no authored machines. Place ammo boxes, wall-buys and the weapon crate in reachable areas.
	/// (Perk machines are turned off until the perk system is revisited, see the commented-out block below.)
	/// </summary>
	private void PlaceBuyStations()
	{
		if ( Scene.GetAllComponents<ZombiesBuyStation>().Any() ) return;

		var spawns = GameUtils.GetSpawnPoints().Select( x => x.Transform.Position ).ToList();
		var center = spawns.Count > 0
			? spawns.Aggregate( Vector3.Zero, ( a, b ) => a + b ) / spawns.Count
			: HumanPawns( Scene ).First().WorldPosition;

		var entries = new List<(ZombiesBuyKind Kind, Action<ZombiesBuyStation> Setup)>();

		// Put back with perks: the perk machines, spread across reachable rooms. With none placed nobody can get a
		// perk, so the perk HUD badges, perk effects and solo Second Wind self-revive never come into play.
		// foreach ( var perk in new[] { ZombiesPerk.SecondWind, ZombiesPerk.IronTonic, ZombiesPerk.BoltSoda, ZombiesPerk.HotShot, ZombiesPerk.FleetFoot } )
		// {
		// 	var p = perk;
		// 	entries.Add( (ZombiesBuyKind.Perk, s => { s.Kind = ZombiesBuyKind.Perk; s.Perk = p; s.Cost = ZombiesBuyStation.PerkCost( p ); }) );
		// }

		var weapons = GetWeaponCratePool().OrderBy( x => x.ResourceName ).ToList();
		var secondary = weapons.FirstOrDefault( x => x.Slot == EquipmentSlot.Secondary );
		var primaries = weapons.Where( x => x.Slot == EquipmentSlot.Primary ).Take( 2 ).ToList();
		if ( secondary is not null )
			entries.Add( (ZombiesBuyKind.WallWeapon, s => { s.Kind = ZombiesBuyKind.WallWeapon; s.WeaponName = secondary.ResourceName; s.Cost = 500; }) );
		for ( int i = 0; i < primaries.Count; i++ )
		{
			var w = primaries[i];
			var cost = 1000 + i * 400;
			entries.Add( (ZombiesBuyKind.WallWeapon, s => { s.Kind = ZombiesBuyKind.WallWeapon; s.WeaponName = w.ResourceName; s.Cost = cost; }) );
		}
		for ( int i = 0; i < 2; i++ )
			entries.Add( (ZombiesBuyKind.AmmoBox, s => { s.Kind = ZombiesBuyKind.AmmoBox; s.Cost = ZombiesBuyStation.AmmoBoxCost; }) );

		// The workbench: attachments, armour, ammo and grenades (ZombiesWorkbench.cs).
		entries.Add( (ZombiesBuyKind.Workbench, s => { s.Kind = ZombiesBuyKind.Workbench; }) );

		entries.Add( (ZombiesBuyKind.WeaponCrate, s => { s.Kind = ZombiesBuyKind.WeaponCrate; s.Cost = ZombiesBuyStation.WeaponCrateCost; }) );

		var centerNav = Scene.NavMesh.GetClosestPoint( center, 400f )
			?? (spawns.Count > 0 ? Scene.NavMesh.GetClosestPoint( spawns[0], 200f ) : null)
			?? center;
		var placed = new List<Vector3>();

		// A map's own spots (ZombiesStationSpot), by kind, lowest Order first.
		var spots = Scene.GetAllComponents<ZombiesStationSpot>()
			.GroupBy( x => x.Kind )
			.ToDictionary( g => g.Key, g => new Queue<ZombiesStationSpot>( g.OrderBy( x => x.Order ) ) );

		for ( int i = 0; i < entries.Count; i++ )
		{
			var (kind, setup) = entries[i];

			if ( spots.TryGetValue( kind, out var queue ) && queue.Count > 0 )
			{
				var spot = queue.Dequeue();
				var at = spot.WorldPosition;
				// A wall spot can start the trace inside its wall (Riverside's office), so then it keeps its own height.
				var floor = Scene.Trace.Ray( at + Vector3.Up * 40f, at + Vector3.Down * 120f ).WithoutTags( "player", "enemy", "trigger" ).Run();
				if ( floor.Hit && !floor.StartedSolid ) at = floor.EndPosition;
				var facing = spot.WorldRotation.Forward.WithZ( 0 );
				placed.Add( at );
				CreateStation( at, Rotation.LookAt( facing.LengthSquared > 0.01f ? facing.Normal : Vector3.Forward ), setup );
				continue;
			}

			var size = StationSize( kind );
			var ring = center + Rotation.FromYaw( 360f / entries.Count * i ).Forward * 420f;
			Vector3 pos;
			Rotation rot;
			var found = (kind == ZombiesBuyKind.Perk || kind == ZombiesBuyKind.AmmoBox || kind == ZombiesBuyKind.Workbench) && placed.Count > 0
				? TryPlaceSpreadStation( centerNav, ring, size, spawns, placed, out pos, out rot )
				: TryPlaceStation( centerNav, ring, size, placed, false, out pos, out rot );

			if ( !found )
			{
				// Search outwards from the spawn area. Indoor nav points can be cramped or disconnected;
				// if the strict search fails, allow spots closer to doors and other stations.
				for ( int attempt = 0; attempt < 800 && !found; attempt++ )
				{
					var radius = 300f + 1300f * (attempt % 400) / 399f;
					if ( Scene.NavMesh.GetRandomPoint( centerNav, radius ) is { } guess )
						found = TryPlaceStation( centerNav, guess, size, placed, attempt >= 400, out pos, out rot );
				}

				if ( !found )
				{
					// Nowhere sensible: fall back to the plain ring spot rather than leave the station out.
					Log.Warning( $"[Zombies] No clear spot for a {kind} station, placing it on the ring." );
					pos = Scene.NavMesh.GetClosestPoint( ring, 400f ) ?? ring;
					var tr = Scene.Trace.Ray( pos + Vector3.Up * 40f, pos + Vector3.Down * 400f ).WithoutTags( "player", "enemy" ).Run();
					if ( tr.Hit ) pos = tr.EndPosition;
					rot = Rotation.LookAt( (center - pos).WithZ( 0 ).Normal );
				}
			}

			placed.Add( pos );
			CreateStation( pos, rot, setup );
		}
	}

	/// <summary>Sample playable spawn areas and pick a reachable station location away from the others.</summary>
	private bool TryPlaceSpreadStation( Vector3 center, Vector3 ring, Vector3 size, List<Vector3> spawns, List<Vector3> placed, out Vector3 position, out Rotation rotation )
	{
		position = default;
		rotation = default;
		var bestSeparation = -1f;

		for ( int pass = 0; pass < 2 && bestSeparation < 450f; pass++ )
		{
			for ( int attempt = 0; attempt < 160; attempt++ )
			{
				Vector3? guess = attempt == 0 ? ring
					: spawns.Count > 0 && attempt % 5 != 0
						? Scene.NavMesh.GetRandomPoint( spawns[(attempt - 1) % spawns.Count], 450f )
						: Scene.NavMesh.GetRandomPoint();
				if ( guess is not { } candidate || !TryPlaceStation( center, candidate, size, placed, pass > 0, out var pos, out var rot ) )
					continue;

				var separation = placed.Min( p => p.Distance( pos ) );
				if ( separation <= bestSeparation )
					continue;

				bestSeparation = separation;
				position = pos;
				rotation = rot;
			}
		}

		return bestSeparation >= 0f;
	}

	/// <summary>Collision size of each kind of station, matching <see cref="CreateStation"/>. X is its depth, front to back.</summary>
	private static Vector3 StationSize( ZombiesBuyKind kind ) => kind switch
	{
		ZombiesBuyKind.Perk => new Vector3( 64f, 64f, 103f ),
		ZombiesBuyKind.WeaponCrate => new Vector3( 36f, 70f, 34f ),
		ZombiesBuyKind.AmmoBox => new Vector3( 40f, 68f, 48f ),
		ZombiesBuyKind.Workbench => new Vector3( 40f, 72f, 86f ),
		_ => new Vector3( 10f, 60f, 60f ),
	};

	/// <summary>
	/// Find a spot for a station near <paramref name="guess"/>: on the navmesh and
	/// walkable from them, clear of walls, doors and other stations. It backs onto a wall if there's one close by,
	/// otherwise it faces the players. <paramref name="relaxed"/> lets it go nearer doors and other stations.
	/// </summary>
	private bool TryPlaceStation( Vector3 center, Vector3 guess, Vector3 size, List<Vector3> placed, bool relaxed, out Vector3 position, out Rotation rotation )
	{
		position = default;
		rotation = default;

		if ( Scene.NavMesh.GetClosestPoint( guess, 96f ) is not { } nav ) return false;

		// Back onto the closest wall, if there's one within reach.
		var pos = nav;
		var forward = (center - nav).WithZ( 0 );
		forward = forward.LengthSquared > 1f ? forward.Normal : Vector3.Forward;
		var closestWall = 100f;
		for ( int i = 0; i < 8; i++ )
		{
			var dir = Rotation.FromYaw( 45f * i ).Forward;
			var start = nav + Vector3.Up * 48f;
			var wall = Scene.Trace.Ray( start, start + dir * 100f )
				.WithoutTags( "player", "enemy", "trigger", TerrorTown.MapMover.DoorTag )
				.Run();
			if ( !wall.Hit || MathF.Abs( wall.Normal.z ) > 0.3f ) continue;

			// Straight-on distance to the wall, the ray may have hit it at an angle.
			var normal = wall.Normal.WithZ( 0 ).Normal;
			var distance = wall.Distance * Vector3.Dot( dir, -normal );
			if ( distance >= closestWall ) continue;

			closestWall = distance;
			forward = normal;
			pos = nav - forward * (distance - size.x * 0.5f - 1f);
		}

		var ground = Scene.Trace.Ray( pos + Vector3.Up * 40f, pos + Vector3.Down * 80f ).WithoutTags( "player", "enemy", "trigger" ).Run();
		if ( !ground.Hit || MathF.Abs( ground.EndPosition.z - nav.z ) > 24f ) return false;
		pos = ground.EndPosition;

		if ( placed.Any( p => p.Distance( pos ) < (relaxed ? 100f : 150f) ) ) return false;

		// Not on top of anyone, or where they'll respawn.
		bool Near( Vector3 p ) => p.WithZ( 0 ).Distance( pos.WithZ( 0 ) ) < 90f && MathF.Abs( p.z - pos.z ) < 72f;
		if ( HumanPawns( Scene ).Any( p => Near( p.WorldPosition ) ) ) return false;
		if ( GameUtils.GetSpawnPoints().Any( s => Near( s.Transform.Position ) ) ) return false;

		// Out of the way of doors swinging open, even for the relaxed search: an ammo box inside a hotel door's swing
		// left too little room between it and the open door to get through.
		if ( Scene.GetAllComponents<TerrorTown.MapMover>().Any( door => InDoorsWay( door, pos, size ) ) ) return false;

		// Nothing in the way of the station itself (lifted off the floor, and a touch smaller so the wall it backs onto doesn't count).
		var rot = Rotation.LookAt( forward );
		var half = (size - 4f) * 0.5f;
		var box = new BBox( new Vector3( -half.x, -half.y, -half.z ), new Vector3( half.x, half.y, half.z ) );
		var middle = pos + Vector3.Up * (size.z * 0.5f + 4f);
		var blocked = Scene.Trace.Box( box, middle, middle )
			.Rotated( rot )
			.WithoutTags( "player", "enemy", "trigger" )
			.Run();
		if ( blocked.Hit || blocked.StartedSolid ) return false;

		// Not across a walkway: room for a player to pass in front, and, standing free of a wall, down one side.
		if ( FreeDistance( middle, rot.Forward ) - size.x * 0.5f < PassWidth ) return false;
		if ( closestWall >= 100f && FreeDistance( middle, rot.Right ) - size.y * 0.5f < PassWidth
			&& FreeDistance( middle, -rot.Right ) - size.y * 0.5f < PassWidth ) return false;

		// Standing room in front, and players can walk to it.
		var front = Scene.NavMesh.GetClosestPoint( pos + forward * (size.x * 0.5f + 40f), 48f );
		if ( front is not { } frontNav || !CanWalk( center, frontNav, 5000f ) ) return false;

		position = pos;
		rotation = rot;
		return true;
	}

	/// <summary> Room a player needs to get past a station: their 32-unit box and a little over. </summary>
	private const float PassWidth = 48f;

	/// <summary>
	/// Whether a station here would be in a door's way: in a hinged door's swing (plus room to get past), or close to
	/// anything else that moves.
	/// </summary>
	private static bool InDoorsWay( TerrorTown.MapMover door, Vector3 pos, Vector3 size )
	{
		if ( door is TerrorTown.FuncDoorRotating hinged )
		{
			var hinge = hinged.HingePosition;
			var reach = hinged.SwingRadius + size.WithZ( 0f ).Length * 0.5f + PassWidth;
			return MathF.Abs( hinge.z - pos.z ) < 120f && hinge.WithZ( 0f ).Distance( pos.WithZ( 0f ) ) < reach;
		}

		var center = door.GetComponent<ModelRenderer>()?.Bounds.Center ?? door.WorldPosition;
		return MathF.Abs( center.z - pos.z ) < 120f && center.WithZ( 0f ).Distance( pos.WithZ( 0f ) ) < 110f;
	}

	/// <summary> How far from a station's middle to the nearest wall that way (doors don't count, they open). </summary>
	private float FreeDistance( Vector3 from, Vector3 direction )
	{
		var tr = Scene.Trace.Ray( from, from + direction * 200f )
			.WithoutTags( "player", "enemy", "trigger", TerrorTown.MapMover.DoorTag )
			.Run();
		return tr.Hit ? tr.Distance : 200f;
	}

	private void CreateStation( Vector3 pos, Rotation rot, Action<ZombiesBuyStation> setup )
	{
		var go = new GameObject( true, "Zombies Buy Station" );
		go.WorldPosition = pos;
		go.WorldRotation = rot;

		var station = go.Components.Create<ZombiesBuyStation>();
		setup( station );

		var color = station.Kind switch
		{
			ZombiesBuyKind.Perk => ZombiesBuyStation.PerkColor( station.Perk ),
			ZombiesBuyKind.WeaponCrate => new Color( 0.3f, 0.6f, 1f ),
			ZombiesBuyKind.AmmoBox => new Color( 0.3f, 1f, 0.35f ),
			ZombiesBuyKind.Workbench => new Color( 1f, 0.72f, 0.35f ),
			_ => new Color( 1f, 0.85f, 0.6f ),
		};

		Vector3 size;
		switch ( station.Kind )
		{
			case ZombiesBuyKind.Perk:
				// Custom soda-fountain dispensers with a distinct illustrated face per perk.
				CreatePerkDispenser( go, station.Perk, color );
				size = new Vector3( 64f, 64f, 103f );
				break;

			case ZombiesBuyKind.WeaponCrate:
				AddFittedModel( go, WeaponCrateModel, 32f, Color.White, lengthAlongY: true );
				size = new Vector3( 36f, 70f, 34f );
				break;

			case ZombiesBuyKind.AmmoBox:
				var crate = new GameObject( go, true, "Ammo box" );
				crate.LocalPosition = Vector3.Up * 26f;
				crate.LocalScale = 2.5f;
				ZombiesPowerUp.CreateAmmoCase( crate );
				size = new Vector3( 40f, 68f, 48f );
				break;

			case ZombiesBuyKind.Workbench:
				ZombiesBuyStation.CreateBenchModel( go );
				size = new Vector3( 40f, 72f, 86f );
				break;

			default:
			{
				// Wall buy: backboard with the actual weapon model on it.
				var board = new GameObject( go, true, "Board" );
				board.LocalPosition = new Vector3( -4f, 0, 40f );
				board.LocalScale = new Vector3( 2f, 60f, 40f ) / 50f;
				var boardModel = board.Components.Create<ModelRenderer>();
				boardModel.Model = Model.Load( "models/dev/box.vmdl" );
				boardModel.Tint = new Color( 0.28f, 0.2f, 0.13f );

				if ( station.Weapon?.WorldModel is { } weaponModel && !weaponModel.IsError )
				{
					var gun = new GameObject( go, true, "Weapon" );
					gun.LocalPosition = new Vector3( 2f, 0, 40f );
					gun.LocalRotation = Rotation.FromYaw( 90f );
					gun.Components.Create<ModelRenderer>().Model = weaponModel;
					var len = Math.Max( weaponModel.Bounds.Size.x, 1f );
					gun.LocalScale = Math.Min( 1.4f, 50f / len );
					gun.LocalPosition -= gun.LocalRotation * weaponModel.Bounds.Center * gun.LocalScale.x;
				}
				size = new Vector3( 10f, 60f, 60f );
				break;
			}
		}

		var collider = go.Components.Create<BoxCollider>();
		collider.Scale = size;
		collider.Center = Vector3.Up * size.z * 0.5f;

		// Glow in front of the station so the model is lit in its colour.
		var lightGo = new GameObject( go, true, "Light" );
		lightGo.LocalPosition = new Vector3( 30f, 0, size.z * 0.8f );
		var light = lightGo.Components.Create<PointLight>();
		light.LightColor = color;
		light.Radius = 160f;

		go.NetworkSpawn( null );
	}

	/// <summary>
	/// Build a pressed-metal soda-fountain dispenser: its enamel in the perk's colour, a poster with the perk's
	/// illustration and a lit name sign on top.
	/// </summary>
	private static void CreatePerkDispenser( GameObject parent, ZombiesPerk perk, Color glow )
	{
		var dark = new Color( 0.055f, 0.065f, 0.058f );
		var steel = new Color( 0.54f, 0.53f, 0.46f );
		// The enamel texture is grey, so this is the paint colour. Keep Assets/Perks/preview_dispenser.py in step.
		var enamel = perk switch
		{
			ZombiesPerk.SecondWind => new Color( 0.16f, 0.30f, 0.58f ),
			ZombiesPerk.BoltSoda => new Color( 0.12f, 0.40f, 0.20f ),
			ZombiesPerk.HotShot => new Color( 0.30f, 0.09f, 0.07f ),
			ZombiesPerk.FleetFoot => new Color( 0.78f, 0.38f, 0.10f ),
			_ => new Color( 0.60f, 0.10f, 0.09f )
		};
		var art = ZombiesBuyStation.PerkArt( perk );

		// These meshes share one origin: the shell, bezel, spout and tray are designed
		// together, instead of being a stack of independently scaled primitives.
		AddPerkMesh( parent, "Pressed enamel cabinet", "Perks/perk_enamel.vmdl", enamel );
		AddPerkMesh( parent, "Cast fittings and bezel", "Perks/perk_metal.vmdl", steel );
		AddPerkMesh( parent, "Recesses and vents", "Perks/perk_dark.vmdl", dark );
		AddPerkMesh( parent, "Perk lamps", "Perks/perk_accent.vmdl", glow );
		AddPerkMesh( parent, $"{perk} poster", "Perks/perk_card.vmdl", Color.White ).MaterialOverride = Material.Load( $"Perks/{art}_poster.vmat" );
		AddPerkMesh( parent, $"{perk} sign", "Perks/perk_sign.vmdl", Color.White ).MaterialOverride = Material.Load( $"Perks/{art}_sign.vmat" );
	}

	private static ModelRenderer AddPerkMesh( GameObject parent, string name, string asset, Color tint )
	{
		var part = new GameObject( parent, true, name );
		var renderer = part.Components.Create<ModelRenderer>();
		renderer.Model = Model.Load( asset );
		renderer.Tint = tint;
		return renderer;
	}

	/// <summary>Adds a model scaled to a target height, sitting on the ground and centred on the station.</summary>
	private static void AddFittedModel( GameObject parent, Model model, float height, Color tint, bool lengthAlongY = false )
	{
		if ( model is null || model.IsError )
		{
			Log.Warning( $"[Zombies] Missing model for {parent.Name}; using a visible fallback." );
			model = Model.Load( "models/dev/box.vmdl" );
		}

		var body = new GameObject( parent, true, "Body" );
		if ( lengthAlongY ) body.LocalRotation = Rotation.FromYaw( 90f );

		var b = model.Bounds;
		var scale = height / Math.Max( b.Size.z, 1f );
		body.LocalScale = scale;
		var centre = new Vector3( b.Center.x, b.Center.y, b.Mins.z ) * scale;
		body.LocalPosition = -(body.LocalRotation * centre);

		var renderer = body.Components.Create<ModelRenderer>();
		renderer.Model = model;
		renderer.Tint = tint;
	}
}
