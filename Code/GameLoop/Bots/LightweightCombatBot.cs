using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A cheap FPS-style combat bot that participates in HC1 teams without becoming a full Client/PlayerPawn.
/// </summary>
public sealed partial class LightweightCombatBot : Component, ITeam, IDescription, IRespawnable, IAreaDamageReceiver, IMarkerObject,
	IGameEventHandler<KillEvent>,
	IGameEventHandler<ResetScoresEvent>,
	IGameEventHandler<DamageTakenEvent>
{
	[Property] public Team Team { get; set; } = Team.Unassigned;
	[Property] public string BotName { get; set; } = "Raven";
	[Property] public HealthComponent HealthComponent { get; set; }
	[Property] public NavMeshAgent Agent { get; set; }
	[Property] public SkinnedModelRenderer Renderer { get; set; }

	[Property, Group( "Combat" )] public float SightRange { get; set; } = 6000f;
	/// <summary> Beyond this the bot holds fire: at that distance a soldier is spotting, not shooting. </summary>
	[Property, Group( "Combat" )] public float EngageRange { get; set; } = 4000f;
	/// <summary> The distance bots like to fight at; aggressive ones get closer, cautious ones hang back. </summary>
	[Property, Group( "Combat" )] public float PreferredRange { get; set; } = 550f;
	/// <summary> Damage per round, before hitbox multipliers. Hardcore kills in one hit regardless. </summary>
	[Property, Group( "Combat" )] public float Damage { get; set; } = 20f;
	[Property, Group( "Combat" )] public float RealPlayerDamageScale { get; set; } = 0.75f;
	/// <summary>Whether this bot's weapon is loaded with tracer rounds. Ordinary ammo has no visible trail.</summary>
	[Property, Group( "Combat" )] public bool UsesTracerRounds { get; set; } = false;
	[Property, Group( "Movement" )] public float MoveSpeed { get; set; } = 230f;
	[Property, Group( "Movement" )] public float PatrolRadius { get; set; } = 900f;
	[Property, Group( "Visuals" ), InlineEditor] public Dictionary<Team, HumanOutfitter.TeamModelEntry> TeamBaseModels { get; set; } = new();
	[Property, Group( "Visuals" )] public string WeaponWorldModelPrefab { get; set; } = "weapons/m4a1/wm_m4a1.prefab";
	[Property, Group( "Combat" )] public EquipmentResource WeaponResource { get; set; } = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
	[Property, Group( "Effects" )] public string MuzzleFlashPrefab { get; set; } = "prefabs/weapon_effects/rifle_muzzleflash.prefab";
	[Property, Group( "Effects" )] public GameObject BloodEffect { get; set; }
	[Property, Group( "Effects" )] public string TracerEffectPrefab { get; set; } = "weapons/common/effects/tracer_9mm.prefab";
	[Property, Group( "Effects" )] public string ShootSound { get; set; } = "sounds/weapons/m4a1/m4_shot.sound";

	public bool IsAlive => HealthComponent.IsValid() && HealthComponent.State == LifeState.Alive;
	public Vector3 EyePosition => WorldPosition + Vector3.Up * (IsCrouching ? 44f : 64f);

	[Sync( SyncFlags.FromHost ), Property, ReadOnly] public int Kills { get; private set; }
	[Sync( SyncFlags.FromHost ), Property, ReadOnly] public int Deaths { get; private set; }
	[Sync( SyncFlags.FromHost ), Property, ReadOnly] public int Score { get; private set; }
	public float Ratio => (float)Kills / (float)Deaths.Clamp( 1, int.MaxValue );

	string IDescription.DisplayName => $"{BotName} BOT";
	Color IDescription.Color => Team.GetColor();
	Type IMarkerObject.MarkerPanelTypeOverride => typeof( UI.LightweightBotMarkerPanel );
	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * 78f;
	bool IMarkerObject.ShowChevron => false;

	bool IMarkerObject.ShouldShow()
	{
		var viewer = Client.Viewer?.PlayerPawn;
		return IsAlive && Team != Team.Unassigned && viewer.IsValid() && viewer.Team == Team;
	}

	private GameObject _weaponModel;
	private GameObject _weaponHold;
	private bool _dying;

	private const int KillScore = 25;
	private const int TeamKillScore = -25;
	private const int SuicideScore = -10;
	private const float TargetMemorySeconds = 8f;
	private const float CorpseLifetime = 15f;

	protected override void OnStart()
	{
		EnsureReferences();
		ConfigureComponents();
		AttachWeaponModel();

		if ( RandomizePersonality && !IsProxy )
			RollPersonality();
	}

	protected override void OnUpdate()
	{
		EnsureReferences();
		AttachWeaponModel();
		UpdateAnimation();

		if ( IsProxy )
			return;

		if ( Networking.IsActive && !Networking.IsHost )
			return;

		if ( !IsAlive )
			return;

		if ( GameUtils.IsCombatFrozen )
		{
			ResetCombatState();
			return;
		}

		Think();
	}

	private void EnsureReferences()
	{
		HealthComponent ??= Components.Get<HealthComponent>();
		Agent ??= Components.Get<NavMeshAgent>();
		Renderer ??= Components.GetInChildren<SkinnedModelRenderer>( true );
	}

	internal void ApplyTeamModel()
	{
		EnsureReferences();
		if ( !Renderer.IsValid() )
			return;

		// Match the player outfitter, including its T-side fallback for free-for-all.
		if ( !TeamBaseModels.TryGetValue( Team, out var entry )
			&& !TeamBaseModels.TryGetValue( Team.Terrorist, out entry ) )
			return;

		if ( entry.Models is { Count: > 0 } )
			Renderer.Model = Game.Random.FromList( entry.Models );
	}

	private void ConfigureComponents()
	{
		GameObject.Tags.Add( LightweightBotManager.BotTag );
		GameObject.Tags.Add( "player" );

		if ( HealthComponent.IsValid() )
		{
			HealthComponent.Health = HealthComponent.MaxHealth;
		}

		if ( Agent.IsValid() )
		{
			Agent.MaxSpeed = MoveSpeed;
			Agent.Radius = MathF.Max( Agent.Radius, 24f );
			Agent.Height = MathF.Max( Agent.Height, 64f );
			Agent.Separation = MathF.Max( Agent.Separation, 1.25f );
			Agent.UpdateRotation = false;
			Agent.UpdatePosition = true;
		}
	}

	private void AttachWeaponModel()
	{
		if ( _dying || _weaponModel.IsValid() || string.IsNullOrWhiteSpace( WeaponWorldModelPrefab ) )
			return;

		if ( !GameObject.GetPrefab( WeaponWorldModelPrefab ).IsValid() )
			return;

		var parent = GetWeaponHold();
		if ( !parent.IsValid() )
			return;

		_weaponModel = GameObject.Clone( WeaponWorldModelPrefab, new CloneConfig
		{
			Name = "M4A1",
			Parent = parent,
			StartEnabled = true
		} );

		if ( !_weaponModel.IsValid() )
			return;

		_weaponModel.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
	}

	private void DropWeaponModel()
	{
		if ( !_weaponModel.IsValid() )
			return;

		var weapon = _weaponModel;
		_weaponModel = null;
		var position = weapon.WorldPosition;
		var rotation = weapon.WorldRotation;
		weapon.Destroy();

		if ( !Networking.IsHost || WeaponResource is null )
			return;

		var dropped = DroppedEquipment.Create( WeaponResource, position, rotation, networkSpawn: false );
		dropped.ApplySavedAttachments = false;
		var templateAmmo = WeaponResource.MainPrefab.IsValid()
			? WeaponResource.MainPrefab.GetComponentInChildren<WeaponAmmo>( true )
			: null;
		var magazineSize = Math.Max( 1, templateAmmo?.MaxAmmo ?? 30 );
		var ammo = dropped.GameObject.Components.Create<WeaponAmmo>();
		ammo.MaxAmmo = magazineSize;
		ammo.Ammo = magazineSize;
		ammo.ReserveAmmo = magazineSize * 2;
		dropped.GameObject.NetworkSpawn();
	}

	private GameObject GetWeaponHold()
	{
		if ( _weaponHold.IsValid() )
			return _weaponHold;

		if ( !Renderer.IsValid() )
			return null;

		var hold = Renderer.GetBoneObject( "hold_r" )
			?? Renderer.GetBoneObject( "hold_R" );

		if ( hold.IsValid() )
			return hold;

		var hand = Renderer.GetBoneObject( "r_hand" )
			?? Renderer.GetBoneObject( "hand_R" );

		if ( !hand.IsValid() )
			return null;

		_weaponHold = new GameObject( true, "WeaponHold" );
		_weaponHold.Parent = hand;
		_weaponHold.LocalPosition = new Vector3( -5.199091f, 1.812593f, 4.880827f );
		_weaponHold.LocalRotation = new Rotation( 0.006424597f, -0.9902432f, 0.04879934f, 0.130368f );

		return _weaponHold;
	}

	[Rpc.Broadcast]
	private void DoShootEffects( Vector3 startPosition, Vector3 endPosition, bool usesTracerRounds )
	{
		EnsureReferences();
		AttachWeaponModel();

		var direction = (endPosition - startPosition).Normal;
		var muzzle = GetWeaponWorldModel()?.Muzzle;

		if ( !string.IsNullOrWhiteSpace( MuzzleFlashPrefab ) && GameObject.GetPrefab( MuzzleFlashPrefab ).IsValid() )
		{
			var flash = muzzle.IsValid()
				? GameObject.Clone( MuzzleFlashPrefab, new CloneConfig { Parent = muzzle, Transform = global::Transform.Zero, StartEnabled = true } )
				: GameObject.Clone( MuzzleFlashPrefab, new CloneConfig { Transform = new Transform( startPosition, Rotation.LookAt( direction ) ), StartEnabled = true } );

			if ( flash.IsValid() )
				flash.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		}

		if ( usesTracerRounds && !string.IsNullOrWhiteSpace( TracerEffectPrefab ) && GameObject.GetPrefab( TracerEffectPrefab ).IsValid() )
		{
			var tracerObject = GameObject.Clone( TracerEffectPrefab, new CloneConfig
			{
				Transform = new Transform( startPosition, Rotation.LookAt( direction ) ),
				StartEnabled = true
			} );

			if ( tracerObject.IsValid() )
			{
				tracerObject.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;

				if ( tracerObject.GetComponentInChildren<Tracer>() is { } tracer )
					tracer.EndPoint = endPosition;
			}
		}

		if ( !string.IsNullOrWhiteSpace( ShootSound ) )
			Sound.Play( ShootSound, startPosition );

		Renderer?.Set( "b_attack", true );
	}

	private Vector3 GetMuzzlePosition()
	{
		var muzzle = GetWeaponWorldModel()?.Muzzle;
		if ( muzzle.IsValid() )
			return muzzle.WorldPosition;

		return EyePosition + WorldRotation.Forward * 32f;
	}

	private WorldModel GetWeaponWorldModel()
	{
		return _weaponModel.IsValid() ? _weaponModel.GetComponentInChildren<WorldModel>() : null;
	}

	private void UpdateAnimation()
	{
		if ( !Renderer.IsValid() )
			return;

		if ( !IsAlive )
			return;

		var velocity = Agent.IsValid() ? Agent.Velocity : Vector3.Zero;
		var forward = WorldRotation.Forward.Dot( velocity );
		var sideward = WorldRotation.Right.Dot( velocity );

		Renderer.Set( "holdtype", (int)AnimationHelper.HoldTypes.Rifle );
		Renderer.Set( "holdtype_handedness", (int)AnimationHelper.Hand.Right );
		Renderer.Set( "b_twohanded", true );
		Renderer.Set( "b_grounded", true );
		Renderer.Set( "move_speed", velocity.Length );
		Renderer.Set( "move_groundspeed", velocity.WithZ( 0f ).Length );
		Renderer.Set( "move_x", forward );
		Renderer.Set( "move_y", sideward );
		Renderer.Set( "move_z", velocity.z );
		Renderer.Set( "speed_move", 1f );

		Renderer.Set( "duck", IsCrouching ? 1f : 0f );

		// The host decides where the bot aims and syncs it, so every client sees it look at what it's shooting.
		var aim = AimDirection.IsNearZeroLength ? WorldRotation.Forward : AimDirection;
		Renderer.SetLookDirection( "aim_eyes", aim, 1f );
		Renderer.SetLookDirection( "aim_head", aim, 1f );
		Renderer.SetLookDirection( "aim_body", aim, 0.75f );
	}

	private bool IsEnemyAlive( Component target )
	{
		if ( !target.IsValid() )
			return false;

		if ( !GameUtils.IsFreeForAllMode && GameUtils.GetTeamFromComponent( target ) == Team )
			return false;

		return target switch
		{
			PlayerPawn player => player.HealthComponent.IsValid() && player.HealthComponent.State == LifeState.Alive
				&& !player.HealthComponent.IsGodMode,
			LightweightCombatBot bot => bot.IsAlive,
			_ => false
		};
	}

	private static bool HitTarget( GameObject hit, Component target )
	{
		if ( !hit.IsValid() || !target.IsValid() )
			return false;

		return hit == target.GameObject || hit.Root == target.GameObject.Root || hit.IsDescendant( target.GameObject );
	}

	void IRespawnable.OnKill( DamageInfo damageInfo )
	{
		if ( _dying )
			return;

		_dying = true;
		GameObject.Tags.Remove( "player" );
		GameObject.Tags.Add( "dead" );
		
		Agent?.Stop();
		if ( Agent.IsValid() )
		{
			Agent.Enabled = false;
		}

		DropWeaponModel();

		if ( Renderer.IsValid() )
		{
			Renderer.UseAnimGraph = false;
			var physics = Renderer.Components.GetOrCreate<Sandbox.ModelPhysics>();
			physics.Enabled = true;

			if ( physics.PhysicsGroup.IsValid() )
			{
				foreach ( var body in physics.PhysicsGroup.Bodies )
				{
					body.ApplyImpulseAt( damageInfo.Position, damageInfo.Force * 50f );
				}
			}
		}

		GameObject.DestroyAsync( CorpseLifetime );
	}

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		if ( !Networking.IsHost )
			return;

		var damageInfo = eventArgs.DamageInfo;
		var killerBot = GameUtils.GetLightweightBotFromComponent( damageInfo.Attacker );
		var victimBot = GameUtils.GetLightweightBotFromComponent( damageInfo.Victim );

		var killerIsThis = killerBot == this;
		var victimIsThis = victimBot == this;
		if ( !killerIsThis && !victimIsThis )
			return;

		var killerTeam = GameUtils.GetTeamFromComponent( damageInfo.Attacker );
		var victimTeam = GameUtils.GetTeamFromComponent( damageInfo.Victim );
		var isFriendly = killerTeam != Team.Unassigned && killerTeam == victimTeam;
		var isSuicide = killerIsThis && victimIsThis;

		if ( killerIsThis )
		{
			if ( isFriendly && !isSuicide )
			{
				Kills--;
				Score += TeamKillScore;
			}
			else if ( isSuicide )
			{
				Kills--;
				Score += SuicideScore;
			}
			else
			{
				Kills++;
				Score += KillScore;
			}
		}

		if ( victimIsThis && !isFriendly )
		{
			Deaths++;
		}
	}

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent eventArgs )
	{
		if ( !Networking.IsHost )
			return;

		Kills = 0;
		Deaths = 0;
		Score = 0;
	}

	void IGameEventHandler<DamageTakenEvent>.OnGameEvent( DamageTakenEvent eventArgs )
	{
		var damageInfo = eventArgs.DamageInfo;
		if ( damageInfo.Damage > 0f && BloodEffect.IsValid() )
		{
			// Splash damage can report the blast origin, well outside the victim.
			var chest = WorldPosition + Vector3.Up * 44f;
			var impact = damageInfo.Position;
			if ( impact.DistanceSquared( chest ) > 32f * 32f )
				impact = chest;
			var effectRotation = damageInfo.Force.IsNearZeroLength
				? WorldRotation
				: Rotation.LookAt( damageInfo.Force.Normal, Vector3.Up );
			var blood = BloodEffect.Clone( new CloneConfig()
			{
				StartEnabled = true,
				Transform = new( impact, effectRotation ),
				Name = $"Blood effect from ({GameObject})"
			} );

			if ( blood.IsValid() && !blood.Components.Get<DestroyAfter>().IsValid() )
				blood.DestroyAsync( 2f );
		}

		if ( !Networking.IsHost )
			return;

		var attacker = damageInfo.Attacker;
		if ( attacker.IsValid() && IsEnemyAlive( attacker ) )
			OnShotBy( attacker );
	}

	void IAreaDamageReceiver.ApplyAreaDamage( AreaDamage component )
	{
		if ( !HealthComponent.IsValid() )
			return;

		var damageInfo = new DamageInfo( component.Attacker, component.Damage, component.Inflictor, component.WorldPosition,
			Flags: component.DamageFlags );
		HealthComponent.TakeDamage( damageInfo );
	}
}

public sealed class LightweightBotManager : SingletonComponent<LightweightBotManager>
{
	public const string BotTag = "hc1_lightweight_bot";

	private static readonly string[] BotNames =
	{
		"Raven", "Ghost", "Blaze", "Viper", "Reaper", "Mako", "Falcon", "Nova", "Atlas", "Echo"
	};

	[Property] public string BotPrefabPath { get; set; } = "prefabs/bots/hc1_combat_bot.prefab";
	[Property] public float MinSpawnDistanceFromPlayers { get; set; } = 900f;

	/// <summary>
	/// Chance a bot spawns at one of the map's own player starts instead of the team spawns.
	/// On Flatgrass those are all in the central building, so this keeps it occupied.
	/// </summary>
	[Property, Range( 0, 1 )] public float MapSpawnChance { get; set; } = 0.35f;

	/// <summary>
	/// Map spawns closer than this to a living player are skipped, so bots don't appear in someone's face.
	/// </summary>
	[Property] public float MapSpawnMinPlayerDistance { get; set; } = 500f;
	[Property] public float MinSpawnDistanceFromBots { get; set; } = 800f;

	private int _nextBotIndex;

	/// <summary> Each bot name's skill and aggression, so a name is the same soldier all match. </summary>
	private readonly Dictionary<string, (float Skill, float Aggression)> _personalities = new();

	public IEnumerable<LightweightCombatBot> Bots => Scene.GetAllComponents<LightweightCombatBot>()
		.Where( x => x.IsValid() && x.GameObject.Tags.Has( BotTag ) );

	public void Maintain( int targetPlayerCount, int maxTeamSize )
	{
		if ( IsProxy )
			return;

		if ( Networking.IsActive && !Networking.IsHost )
			return;

		RemoveLegacyClientBots();

		if ( GameUtils.IsFreeForAllMode )
		{
			MaintainFreeForAll( targetPlayerCount );
			return;
		}

		var targetPerTeam = Math.Max( 1, Math.Min( maxTeamSize, targetPlayerCount / 2 ) );
		MaintainTeam( Team.Terrorist, targetPerTeam );
		MaintainTeam( Team.CounterTerrorist, targetPerTeam );
	}

	private void MaintainFreeForAll( int targetPlayerCount )
	{
		var realPlayers = GameUtils.AllPlayers.Count( x => x.IsConnected && !x.IsBot );
		var bots = Bots.Where( x => x.IsAlive ).ToList();

		while ( realPlayers + bots.Count > targetPlayerCount && bots.Count > 0 )
		{
			var bot = bots[^1];
			bots.RemoveAt( bots.Count - 1 );
			bot.GameObject.Destroy();
		}

		while ( realPlayers + bots.Count < targetPlayerCount )
		{
			var bot = SpawnBot( Team.Unassigned );
			if ( !bot.IsValid() )
				break;

			bots.Add( bot );
		}
	}

	private void MaintainTeam( Team team, int targetTeamSize )
	{
		var realPlayers = GameUtils.GetPlayers( team ).Count( x => x.IsConnected && !x.IsBot );
		var bots = Bots.Where( x => x.IsAlive && x.Team == team ).ToList();

		while ( realPlayers + bots.Count > targetTeamSize && bots.Count > 0 )
		{
			var bot = bots[^1];
			bots.RemoveAt( bots.Count - 1 );
			bot.GameObject.Destroy();
		}

		while ( realPlayers + bots.Count < targetTeamSize )
		{
			var bot = SpawnBot( team );
			if ( !bot.IsValid() )
				break;

			bots.Add( bot );
		}
	}

	public LightweightCombatBot SpawnBot( Team team )
	{
		if ( !GameObject.GetPrefab( BotPrefabPath ).IsValid() )
		{
			Log.Warning( $"Missing lightweight bot prefab: {BotPrefabPath}" );
			return null;
		}

		var index = _nextBotIndex++;
		var botObject = GameObject.Clone( BotPrefabPath, new CloneConfig
		{
			Name = $"Combat Bot {index + 1}",
			StartEnabled = false,
			Transform = GetSpawnTransform( team )
		} );

		if ( !botObject.IsValid() )
			return null;

		botObject.Flags |= GameObjectFlags.NotSaved;
		botObject.Tags.Add( BotTag );
		botObject.Tags.Add( "removable" );

		var bot = botObject.Components.Get<LightweightCombatBot>( true );
		if ( bot.IsValid() )
		{
			bot.Team = team;
			bot.BotName = BotNames[index % BotNames.Length];
			if ( !_personalities.TryGetValue( bot.BotName, out var personality ) )
				_personalities[bot.BotName] = personality = (LightweightCombatBot.RollSkill(), Random.Shared.Float( 0.15f, 0.95f ));
			bot.Skill = personality.Skill;
			bot.Aggression = personality.Aggression;
			bot.RandomizePersonality = false;
			// Select the body before networking and creating its weapon attachment bones.
			bot.ApplyTeamModel();
		}

		if ( Networking.IsActive )
		{
			botObject.NetworkSpawn( true, null );
		}
		else
		{
			botObject.Enabled = true;
		}

		return bot;
	}

	public void ClearBots()
	{
		foreach ( var bot in Bots.ToArray() )
		{
			bot.GameObject.Destroy();
		}
	}

	private void RemoveLegacyClientBots()
	{
		foreach ( var clientBot in GameUtils.AllPlayers.Where( x => x.IsValid() && x.IsBot ).ToArray() )
		{
			clientBot.Kick( "Using lightweight NPC bots" );
		}
	}

	private Transform GetSpawnTransform( Team team )
	{
		if ( MapSpawnSettings.MapSpawnPointsAllowed && Random.Shared.Float() < MapSpawnChance && TryGetMapSpawn( out var mapSpawn ) )
			return mapSpawn;
		if ( MapSpawnSettings.NavMeshSpawnsAllowed && TryGetNavSpawn( out var navSpawn ) )
			return navSpawn;

		var spawnPoints = (team == Team.Unassigned ? GameUtils.GetSpawnPoints() : GameUtils.GetSpawnPoints( team )).ToArray();
		if ( spawnPoints.Length == 0 )
			return global::Transform.Zero;

		var candidates = spawnPoints
			.OrderByDescending( x => GetSpawnScore( x.Position ) )
			.Take( Math.Min( spawnPoints.Length, 5 ) )
			.ToArray();

		var spawn = Random.Shared.FromArray( candidates, spawnPoints[0] );
		return spawn.Transform.WithScale( 1f );
	}

	/// <summary>Spread new bots over navigable ground when authored spawn points are occupied.</summary>
	private bool TryGetNavSpawn( out Transform transform )
	{
		transform = global::Transform.Zero;
		var players = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.WorldPosition )
			.ToArray();
		var bots = Bots
			.Where( x => x.IsValid() && x.IsAlive )
			.Select( x => x.WorldPosition )
			.ToArray();
		var candidates = new List<(Vector3 Position, float Score)>();
		for ( var i = 0; i < 32; i++ )
		{
			var point = Scene.NavMesh.GetRandomPoint();
			if ( !point.HasValue )
				break;

			var playerDistance = players.Select( x => x.Distance( point.Value ) )
				.DefaultIfEmpty( MinSpawnDistanceFromPlayers ).Min();
			var botDistance = bots.Select( x => x.Distance( point.Value ) )
				.DefaultIfEmpty( MinSpawnDistanceFromBots ).Min();
			if ( playerDistance < MinSpawnDistanceFromPlayers || botDistance < MinSpawnDistanceFromBots )
				continue;

			var score = MathF.Min( playerDistance, 3000f ) * 0.5f + MathF.Min( botDistance, 3000f );
			candidates.Add( (point.Value, score) );
		}

		if ( candidates.Count == 0 )
			return false;

		var safePoints = candidates.OrderByDescending( x => x.Score ).Take( 5 ).ToArray();
		var chosen = Random.Shared.FromArray( safePoints );
		transform = new Transform( chosen.Position, Rotation.Identity );
		return true;
	}

	/// <summary>
	/// Pick a free map-authored spawn (info_player_start) that no living player is standing near.
	/// </summary>
	private bool TryGetMapSpawn( out Transform transform )
	{
		transform = global::Transform.Zero;

		var players = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.WorldPosition )
			.ToArray();
		var bots = Bots
			.Where( x => x.IsValid() && x.IsAlive )
			.Select( x => x.WorldPosition )
			.ToArray();

		var candidates = Scene.GetAllComponents<SpawnPoint>()
			.Select( x => x.Transform.World )
			.Where( t => players.All( p => p.Distance( t.Position ) > MapSpawnMinPlayerDistance ) )
			.Where( t => bots.All( b => b.Distance( t.Position ) > MinSpawnDistanceFromBots ) )
			.ToArray();

		if ( candidates.Length == 0 ) return false;

		transform = Random.Shared.FromArray( candidates ).WithScale( 1f );
		return true;
	}

	private float GetSpawnScore( Vector3 position )
	{
		var playerDistance = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.WorldPosition.Distance( position ) )
			.DefaultIfEmpty( MinSpawnDistanceFromPlayers )
			.Min();

		var botDistance = Bots
			.Where( x => x.IsValid() && x.IsAlive )
			.Select( x => x.WorldPosition.Distance( position ) )
			.DefaultIfEmpty( MinSpawnDistanceFromBots )
			.Min();

		return playerDistance + botDistance * 0.5f;
	}
}
