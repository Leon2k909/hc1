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

	[Sync( SyncFlags.FromHost )] public TimeUntil InstaKillTime { get; private set; }
	[Sync( SyncFlags.FromHost )] public TimeUntil DoublePointsTime { get; private set; }

	[Property] public GameObject ZombiePrefab { get; set; }
	[Property] public Model ZombieBodyModel { get; set; }
	[Property] public Model MysteryBoxModel { get; set; }

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

		InstaKillTime = 0;
		DoublePointsTime = 0;
		// Wait for the first player; the intro then counts down to round 1.
		BeginIntermission( 9999f );
	}

	/// <summary>Pause or resume the Zombies match from the pause menu.</summary>
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
		IsPaused = paused;
		ApplyPauseTimeScale();
	}

	// ── Queries ─────────────────────────────────────────────────────────────────
	public bool IsPowerUpActive( ZombiesPowerUpType type ) => type switch
	{
		ZombiesPowerUpType.InstaKill => InstaKillTime > 0,
		ZombiesPowerUpType.DoublePoints => DoublePointsTime > 0,
		_ => false
	};

	/// <summary>Real players (not bots) who currently have a pawn in the game.</summary>
	private static IEnumerable<PlayerPawn> HumanPawns( Scene scene ) => scene.GetAllComponents<PlayerPawn>()
		.Where( p => p.IsValid() && p.Client.IsValid() && !p.Client.IsBot );

	/// <summary>Players who are alive and on their feet (or about to be, via solo Quick Revive).</summary>
	public static int CountActivePlayers()
	{
		var scene = Game.ActiveScene;
		if ( scene is null ) return 0;
		return HumanPawns( scene ).Count( p => p.HealthComponent.State == LifeState.Alive
			&& ZombiesPlayerState.For( p ) is not { IsDowned: true, IsSelfReviving: false } );
	}

	/// <summary>Real players in the game, whatever state they're in.</summary>
	public static int CountHumanPlayers() => GameUtils.AllPlayers.Count( c => c.IsConnected && !c.IsBot );

	public static IEnumerable<EquipmentResource> GetMysteryBoxPool() => ResourceLibrary.GetAll<EquipmentResource>()
		.Where( x => (x.Slot == EquipmentSlot.Primary || x.Slot == EquipmentSlot.Secondary)
			&& x.ViewModelPrefab.IsValid() && x.MainPrefab.IsValid()
			&& !Gunsmith.GunsmithLoadoutManager.IsMergedWeaponResource( x ) );

	/// <summary>Held players wait out the round dead, CoD-style, and come back at the next one.</summary>
	public bool ShouldHoldRespawn( Client client ) => client.IsValid() && _heldClients.Contains( client );

	// ── Round flow ──────────────────────────────────────────────────────────────
	protected override void OnUpdate()
	{
		ApplyPauseTimeScale();
		if ( !Networking.IsHost ) return;

		RemoveCombatBots();
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

		if ( _anyoneSpawned && CountActivePlayers() == 0 && GameUtils.AllPlayers.Any( c => c.IsConnected && !c.IsBot ) )
		{
			GameOver();
			return;
		}

		if ( IsIntermission )
		{
			if ( TimeUntilNextRound <= 0 ) StartNextRound();
			return;
		}

		if ( ZombiesRemainingInRound > 0 && ZombiesAlive < GetMaxZombiesAllowed() && _lastSpawnTime > GetSpawnRate() )
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
		foreach ( var pawn in HumanPawns( Scene ) )
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

		BroadcastSound( "sounds/music/round_intro/round_start.sound" );
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
		InstaKillTime = 0;
		DoublePointsTime = 0;
		_heldClients.Clear();

		// Fresh pawns give everyone their starting loadout back.
		foreach ( var client in GameUtils.AllPlayers.Where( c => c.IsConnected && !c.IsBot ).ToList() )
			client.Respawn( true );

		// Old pawns saved their points as they were destroyed; a new game starts from scratch.
		ZombiesGameMode.CarriedPoints.Clear();
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

	private int GetMaxZombiesAllowed() => Math.Min( 24 + 6 * (PlayerCount - 1), 10 + CurrentRound * 2 );

	private float GetSpawnRate() => Math.Max( 0.4f, 2.0f - CurrentRound * 0.1f );

	private bool TryFindSpawnPosition( out Vector3 position )
	{
		position = default;

		var targets = HumanPawns( Scene ).Where( p => p.HealthComponent.State == LifeState.Alive ).ToList();
		if ( targets.Count == 0 ) return false;

		float NearestPlayer( Vector3 pos ) => targets.Min( p => p.WorldPosition.Distance( pos ) );

		// Prefer map spawn points that are out of the players' faces but not miles away.
		var points = Scene.GetAllComponents<SpawnPoint>()
			.Select( x => x.WorldPosition )
			.Where( p => { var d = NearestPlayer( p ); return d > 700f && d < 2600f; } )
			.ToList();

		if ( points.Count > 0 )
		{
			position = points[Game.Random.Int( 0, points.Count - 1 )];
			return true;
		}

		// Otherwise pick a navmesh point in a ring around a random player.
		for ( int i = 0; i < 12; i++ )
		{
			var target = targets[Game.Random.Int( 0, targets.Count - 1 )];
			var dir = Vector3.Random.WithZ( 0 ).Normal;
			var guess = target.WorldPosition + dir * Game.Random.Float( 900f, 1500f );
			var nav = Scene.NavMesh.GetClosestPoint( guess, 400f );
			if ( nav is not { } p ) continue;
			if ( NearestPlayer( p ) < 600f ) continue;

			position = p;
			return true;
		}

		return false;
	}

	/// <summary>Zombies is co-op against zombies only: clear out any deathmatch combat bots.</summary>
	private void RemoveCombatBots()
	{
		foreach ( var bot in Scene.GetAllComponents<LightweightCombatBot>().ToList() )
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
			// an invisible animated human drives it through bone merge.
			var renderer = zombie.Components.Create<SkinnedModelRenderer>();
			renderer.Model = Model.Load( ZombieAI.DriverModel );
			renderer.UseAnimGraph = true;
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
			case ZombiesPowerUpType.MaxAmmo:
				foreach ( var pawn in HumanPawns( Scene ) )
					if ( pawn.HealthComponent.State == LifeState.Alive ) pawn.Inventory.RefillAmmo();
				break;

			case ZombiesPowerUpType.InstaKill:
				InstaKillTime = PowerUpDuration;
				break;

			case ZombiesPowerUpType.DoublePoints:
				DoublePointsTime = PowerUpDuration;
				break;

			case ZombiesPowerUpType.Nuke:
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
	/// The zombies maps have no authored machines, so lay out perk machines, wall-buys and the
	/// mystery box in a ring around where players spawn.
	/// </summary>
	private void PlaceBuyStations()
	{
		if ( Scene.GetAllComponents<ZombiesBuyStation>().Any() ) return;

		var spawns = Scene.GetAllComponents<SpawnPoint>().Select( x => x.WorldPosition ).ToList();
		var center = spawns.Count > 0
			? spawns.Aggregate( Vector3.Zero, ( a, b ) => a + b ) / spawns.Count
			: HumanPawns( Scene ).First().WorldPosition;

		var entries = new List<Action<ZombiesBuyStation>>();

		foreach ( var perk in new[] { ZombiesPerk.QuickRevive, ZombiesPerk.Juggernog, ZombiesPerk.SpeedCola, ZombiesPerk.DoubleTap, ZombiesPerk.StaminUp } )
		{
			var p = perk;
			entries.Add( s => { s.Kind = ZombiesBuyKind.Perk; s.Perk = p; s.Cost = ZombiesBuyStation.PerkCost( p ); } );
		}

		var weapons = GetMysteryBoxPool().OrderBy( x => x.ResourceName ).ToList();
		var secondary = weapons.FirstOrDefault( x => x.Slot == EquipmentSlot.Secondary );
		var primaries = weapons.Where( x => x.Slot == EquipmentSlot.Primary ).Take( 2 ).ToList();
		if ( secondary is not null ) entries.Add( s => { s.Kind = ZombiesBuyKind.WallWeapon; s.WeaponName = secondary.ResourceName; s.Cost = 500; } );
		for ( int i = 0; i < primaries.Count; i++ )
		{
			var w = primaries[i];
			var cost = 1000 + i * 400;
			entries.Add( s => { s.Kind = ZombiesBuyKind.WallWeapon; s.WeaponName = w.ResourceName; s.Cost = cost; } );
		}

		entries.Add( s => { s.Kind = ZombiesBuyKind.MysteryBox; s.Cost = ZombiesBuyStation.MysteryBoxCost; } );

		for ( int i = 0; i < entries.Count; i++ )
		{
			var angle = 360f / entries.Count * i;
			var pos = center + Rotation.FromYaw( angle ).Forward * 420f;

			var tr = Scene.Trace.Ray( pos + Vector3.Up * 400f, pos + Vector3.Down * 800f ).WithoutTags( "player", "enemy" ).Run();
			if ( tr.Hit ) pos = tr.EndPosition;

			CreateStation( pos, Rotation.LookAt( (center - pos).WithZ( 0 ).Normal ), entries[i] );
		}
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
			ZombiesBuyKind.MysteryBox => new Color( 0.3f, 0.6f, 1f ),
			_ => new Color( 1f, 0.85f, 0.6f ),
		};

		Vector3 size;
		switch ( station.Kind )
		{
			case ZombiesBuyKind.Perk:
				// Custom soda-fountain dispensers with a distinct illustrated face per perk.
				CreatePerkDispenser( go, station.Perk, color );
				size = new Vector3( 64f, 64f, 92f );
				break;

			case ZombiesBuyKind.MysteryBox:
				AddFittedModel( go, MysteryBoxModel, 32f, Color.White, lengthAlongY: true );
				size = new Vector3( 36f, 70f, 34f );
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

	/// <summary>Build a pressed-metal soda-fountain dispenser with a unique illustrated face for each perk.</summary>
	private static void CreatePerkDispenser( GameObject parent, ZombiesPerk perk, Color glow )
	{
		var dark = new Color( 0.055f, 0.065f, 0.058f );
		var steel = new Color( 0.54f, 0.53f, 0.46f );

		// These meshes share one origin: the shell, bezel, spout and tray are designed
		// together, instead of being a stack of independently scaled primitives.
		AddPerkMesh( parent, "Pressed enamel cabinet", "Perks/perk_enamel.vmdl", Color.White );
		AddPerkMesh( parent, "Cast fittings and bezel", "Perks/perk_metal.vmdl", steel );
		AddPerkMesh( parent, "Recesses and vents", "Perks/perk_dark.vmdl", dark );
		AddPerkMesh( parent, "Perk lamps", "Perks/perk_accent.vmdl", glow );

		var face = AddStationPart( parent, $"{perk} illustrated face", new Vector3( 29.18f, 0, 58 ), new Vector3( 0.18f, 29.6f, 42.6f ), Color.White, standardBox: true );
		var decal = perk switch
		{
			ZombiesPerk.QuickRevive => "Perks/quickrevive_label.vmat",
			ZombiesPerk.SpeedCola => "Perks/speedcola_label.vmat",
			ZombiesPerk.DoubleTap => "Perks/doubletap_label.vmat",
			ZombiesPerk.StaminUp => "Perks/staminup_label.vmat",
			_ => "Perks/juggernog_label.vmat"
		};
		face.MaterialOverride = Material.Load( decal );

	}

	private static ModelRenderer AddPerkMesh( GameObject parent, string name, string asset, Color tint )
	{
		var part = new GameObject( parent, true, name );
		var renderer = part.Components.Create<ModelRenderer>();
		renderer.Model = Model.Load( asset );
		renderer.Tint = tint;
		return renderer;
	}

	private static ModelRenderer AddStationPart( GameObject parent, string name, Vector3 center, Vector3 size, Color tint, bool standardBox = false, string modelAsset = null )
	{
		var part = new GameObject( parent, true, name );
		var renderer = part.Components.Create<ModelRenderer>();
		renderer.Model = Model.Load( modelAsset ?? (standardBox ? "models/dev/box.vmdl" : "Perks/bevel_box.vmdl") );
		renderer.Tint = tint;
		var bounds = renderer.Model.Bounds;
		part.LocalScale = new Vector3( size.x / bounds.Size.x, size.y / bounds.Size.y, size.z / bounds.Size.z );
		part.LocalPosition = center - bounds.Center * part.LocalScale;
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
