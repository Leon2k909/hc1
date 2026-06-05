using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A cheap FPS-style combat bot that participates in HC1 teams without becoming a full Client/PlayerPawn.
/// </summary>
public sealed class LightweightCombatBot : Component, ITeam, IDescription, IRespawnable, IAreaDamageReceiver, IMarkerObject,
	IGameEventHandler<KillEvent>,
	IGameEventHandler<ResetScoresEvent>,
	IGameEventHandler<DamageTakenEvent>
{
	[Property] public Team Team { get; set; } = Team.Unassigned;
	[Property] public string BotName { get; set; } = "Raven";
	[Property] public HealthComponent HealthComponent { get; set; }
	[Property] public NavMeshAgent Agent { get; set; }
	[Property] public SkinnedModelRenderer Renderer { get; set; }

	[Property, Group( "Combat" )] public float SightRange { get; set; } = 2600f;
	[Property, Group( "Combat" )] public float AttackRange { get; set; } = 1200f;
	[Property, Group( "Combat" )] public float PreferredRange { get; set; } = 900f;
	[Property, Group( "Combat" )] public float FireInterval { get; set; } = 0.55f;
	[Property, Group( "Combat" )] public float Damage { get; set; } = 10f;
	[Property, Group( "Combat" )] public float RealPlayerDamageScale { get; set; } = 0.25f;
	[Property, Group( "Combat" )] public float AimError { get; set; } = 140f;
	[Property, Group( "Movement" )] public float MoveSpeed { get; set; } = 180f;
	[Property, Group( "Movement" )] public float PatrolRadius { get; set; } = 900f;
	[Property, Group( "Visuals" )] public string WeaponWorldModelPrefab { get; set; } = "weapons/m4a1/wm_m4a1.prefab";
	[Property, Group( "Effects" )] public string MuzzleFlashPrefab { get; set; } = "prefabs/weapon_effects/rifle_muzzleflash.prefab";
	[Property, Group( "Effects" )] public string TracerEffectPrefab { get; set; } = "weapons/common/effects/tracer_9mm.prefab";
	[Property, Group( "Effects" )] public string ShootSound { get; set; } = "sounds/weapons/m4a1/m4_shot.sound";

	public bool IsAlive => HealthComponent.IsValid() && HealthComponent.State == LifeState.Alive;
	public Vector3 EyePosition => WorldPosition + Vector3.Up * 64f;

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

	private Component _target;
	private GameObject _weaponModel;
	private GameObject _weaponHold;
	private Vector3? _patrolTarget;
	private TimeSince _timeSinceTargetScan;
	private TimeSince _timeSinceLastShot;
	private TimeSince _timeSincePatrolPick;
	private bool _dying;
	private float _nextFireDelay = 0.55f;
	private int _burstShotsRemaining;
	private TimeSince _timeSinceLastSeen;

	private const int KillScore = 25;
	private const int TeamKillScore = -25;
	private const int SuicideScore = -10;

	protected override void OnStart()
	{
		EnsureReferences();
		ConfigureComponents();
		AttachWeaponModel();
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
			_target = null;
			Agent?.Stop();
			return;
		}

		UpdateTarget();
		UpdateMovement();
		UpdateShooting();
	}

	private void EnsureReferences()
	{
		HealthComponent ??= Components.Get<HealthComponent>();
		Agent ??= Components.Get<NavMeshAgent>();
		Renderer ??= Components.GetInChildren<SkinnedModelRenderer>( true );
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
		if ( _weaponModel.IsValid() || string.IsNullOrWhiteSpace( WeaponWorldModelPrefab ) )
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

	private void UpdateTarget()
	{
		if ( _target.IsValid() && IsEnemyAlive( _target ) )
		{
			if ( HasLineOfSight( _target ) )
			{
				_timeSinceLastSeen = 0f;
			}

			if ( _timeSinceLastSeen < 3f && WorldPosition.DistanceSquared( GetAimPosition( _target ) ) < SightRange * SightRange )
			{
				return;
			}
		}

		if ( _timeSinceTargetScan < 0.25f )
			return;

		_timeSinceTargetScan = 0f;
		_target = FindNearestEnemy();
		if ( _target.IsValid() )
		{
			_timeSinceLastSeen = 0f;
		}
	}

	private Component FindNearestEnemy()
	{
		var bestDistance = SightRange * SightRange;
		Component best = null;
		var freeForAll = GameUtils.IsFreeForAllMode;

		foreach ( var bot in GameUtils.LightweightBots )
		{
			if ( bot == this || !bot.IsValid() || !bot.IsAlive || (!freeForAll && bot.Team == Team) )
				continue;

			if ( !HasLineOfSight( bot ) )
				continue;

			var distance = WorldPosition.DistanceSquared( bot.WorldPosition );
			if ( distance < bestDistance )
			{
				bestDistance = distance;
				best = bot;
			}
		}

		foreach ( var player in GameUtils.PlayerPawns )
		{
			if ( !player.IsValid() || player.HealthComponent.State != LifeState.Alive || (!freeForAll && player.Team == Team) )
				continue;

			if ( !HasLineOfSight( player ) )
				continue;

			var distance = WorldPosition.DistanceSquared( player.WorldPosition );
			if ( distance < bestDistance )
			{
				bestDistance = distance;
				best = player;
			}
		}

		return best;
	}

	private void UpdateMovement()
	{
		if ( !Agent.IsValid() )
			return;

		Agent.MaxSpeed = MoveSpeed;

		if ( _target.IsValid() && IsEnemyAlive( _target ) )
		{
			var targetPosition = GetAimPosition( _target ).WithZ( WorldPosition.z );
			var toTarget = targetPosition - WorldPosition;

			if ( toTarget.LengthSquared > 4f )
			{
				Rotation desiredRotation;
				if ( HasLineOfSight( _target ) )
				{
					desiredRotation = Rotation.LookAt( toTarget.Normal, Vector3.Up );
				}
				else if ( Agent.Velocity.LengthSquared > 10f )
				{
					desiredRotation = Rotation.LookAt( Agent.Velocity.WithZ( 0 ).Normal, Vector3.Up );
				}
				else
				{
					desiredRotation = WorldRotation;
				}
				WorldRotation = Rotation.Lerp( WorldRotation, desiredRotation, Time.Delta * 8f );
			}

			if ( WorldPosition.DistanceSquared( targetPosition ) > PreferredRange * PreferredRange || !HasLineOfSight( _target ) )
			{
				Agent.MoveTo( targetPosition );
			}
			else
			{
				Agent.Stop();
			}

			return;
		}

		UpdatePatrol();

		if ( Agent.Velocity.LengthSquared > 10f )
		{
			var patrolRotation = Rotation.LookAt( Agent.Velocity.WithZ( 0 ).Normal, Vector3.Up );
			WorldRotation = Rotation.Lerp( WorldRotation, patrolRotation, Time.Delta * 8f );
		}
	}

	private void UpdatePatrol()
	{
		if ( !Agent.IsValid() )
			return;

		if ( !_patrolTarget.HasValue || _timeSincePatrolPick > 4f || WorldPosition.DistanceSquared( _patrolTarget.Value ) < 96f * 96f )
		{
			_timeSincePatrolPick = 0f;
			_patrolTarget = FindPatrolTarget();
		}

		if ( _patrolTarget.HasValue )
		{
			Agent.MoveTo( _patrolTarget.Value );
		}
	}

	private Vector3 FindPatrolTarget()
	{
		// Hardpoint game mode integration: capture active hardpoint
		var activeHardpoints = Scene.GetAllComponents<HardpointZone>().ToList();
		if ( activeHardpoints.Count > 0 )
		{
			var targetZone = Game.Random.FromList( activeHardpoints );
			var offset = Vector3.Random.WithZ( 0 ).Normal * Game.Random.Float( 30f, 90f );
			var targetPos = targetZone.WorldPosition + offset;
			return Scene.NavMesh.GetClosestPoint( targetPos ) ?? targetPos;
		}

		// Domination game mode integration: capture active flags
		var activeFlags = Scene.GetAllComponents<DominationFlag>().ToList();
		if ( activeFlags.Count > 0 )
		{
			var enemyFlags = activeFlags.Where( x => x.ControllingTeam != Team ).ToList();
			if ( enemyFlags.Count > 0 )
			{
				// Go to a random uncapped/enemy flag to capture it
				var targetFlag = Game.Random.FromList( enemyFlags );
				var offset = Vector3.Random.WithZ( 0 ).Normal * Game.Random.Float( 30f, 90f );
				var targetPos = targetFlag.WorldPosition + offset;
				return Scene.NavMesh.GetClosestPoint( targetPos ) ?? targetPos;
			}
			else
			{
				// All flags controlled! Choose a random one to defend
				var targetFlag = Game.Random.FromList( activeFlags );
				var offset = Vector3.Random.WithZ( 0 ).Normal * Game.Random.Float( 30f, 90f );
				var targetPos = targetFlag.WorldPosition + offset;
				return Scene.NavMesh.GetClosestPoint( targetPos ) ?? targetPos;
			}
		}

		// Fallback to random patrol
		var direction = Vector3.Random.WithZ( 0f );
		if ( direction.LengthSquared < 0.01f )
		{
			direction = WorldRotation.Forward;
		}

		var candidate = WorldPosition + direction.Normal * Game.Random.Float( PatrolRadius * 0.35f, PatrolRadius );
		return Scene.NavMesh.GetClosestPoint( candidate ) ?? candidate;
	}

	private void UpdateShooting()
	{
		if ( !_target.IsValid() || !IsEnemyAlive( _target ) )
			return;

		if ( _timeSinceLastShot < _nextFireDelay )
			return;

		if ( !HasLineOfSight( _target ) )
			return;

		var aimPosition = GetAimPosition( _target );
		if ( EyePosition.DistanceSquared( aimPosition ) > AttackRange * AttackRange )
			return;

		var noisyAim = aimPosition + Vector3.Random * (AimError * 0.35f);
		var trace = Scene.Trace.Ray( EyePosition, noisyAim )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "playerclip", "movement" )
			.UseHitboxes()
			.Run();

		_timeSinceLastShot = 0f;
		
		if ( _burstShotsRemaining > 0 )
		{
			_burstShotsRemaining--;
			_nextFireDelay = FireInterval * Game.Random.Float( 0.2f, 0.4f );
		}
		else
		{
			if ( Game.Random.Float() < 0.4f )
			{
				_burstShotsRemaining = Game.Random.Int( 2, 5 );
				_nextFireDelay = FireInterval * Game.Random.Float( 0.2f, 0.4f );
			}
			else
			{
				_burstShotsRemaining = 0;
				_nextFireDelay = FireInterval * Game.Random.Float( 0.75f, 1.4f );
			}
		}

		Renderer?.Set( "b_attack", true );
		DoShootEffects( GetMuzzlePosition(), trace.EndPosition );

		if ( !trace.Hit || !HitTarget( trace.GameObject, _target ) )
			return;

		var hitbox = trace.GetHitboxTags();
		if ( hitbox == HitboxTags.None )
		{
			hitbox = HitboxTags.Chest;
		}

		var direction = (trace.EndPosition - EyePosition).Normal;
		var damage = _target is PlayerPawn ? Damage * RealPlayerDamageScale : Damage;
		var damageInfo = new DamageInfo( this, damage, this, trace.EndPosition, direction * damage, hitbox );

		switch ( _target )
		{
			case PlayerPawn player when player.HealthComponent.IsValid():
				player.HealthComponent.TakeDamage( damageInfo );
				break;
			case LightweightCombatBot bot when bot.HealthComponent.IsValid():
				bot.HealthComponent.TakeDamage( damageInfo );
				break;
		}
	}

	[Rpc.Broadcast]
	private void DoShootEffects( Vector3 startPosition, Vector3 endPosition )
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

		if ( !string.IsNullOrWhiteSpace( TracerEffectPrefab ) && GameObject.GetPrefab( TracerEffectPrefab ).IsValid() )
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

		if ( _target.IsValid() && IsEnemyAlive( _target ) && HasLineOfSight( _target ) )
		{
			var direction = (GetAimPosition( _target ) - EyePosition).Normal;
			Renderer.SetLookDirection( "aim_eyes", direction, 1f );
			Renderer.SetLookDirection( "aim_head", direction, 1f );
			Renderer.SetLookDirection( "aim_body", direction, 0.75f );
		}
		else
		{
			var dir = velocity.LengthSquared > 1f ? velocity.Normal : WorldRotation.Forward;
			Renderer.SetLookDirection( "aim_eyes", dir, 1f );
			Renderer.SetLookDirection( "aim_head", dir, 1f );
			Renderer.SetLookDirection( "aim_body", dir, 0.75f );
		}
	}

	private bool IsEnemyAlive( Component target )
	{
		if ( !target.IsValid() )
			return false;

		if ( !GameUtils.IsFreeForAllMode && GameUtils.GetTeamFromComponent( target ) == Team )
			return false;

		return target switch
		{
			PlayerPawn player => player.HealthComponent.IsValid() && player.HealthComponent.State == LifeState.Alive,
			LightweightCombatBot bot => bot.IsAlive,
			_ => false
		};
	}

	private static Vector3 GetAimPosition( Component target )
	{
		return target switch
		{
			PlayerPawn player => player.EyePosition,
			LightweightCombatBot bot => bot.EyePosition,
			_ => target.WorldPosition + Vector3.Up * 48f
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

		GameObject.DestroyAsync( 4.0f );
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
		if ( !Networking.IsHost )
			return;

		var attacker = eventArgs.DamageInfo.Attacker;
		if ( attacker.IsValid() && IsEnemyAlive( attacker ) )
		{
			// Prioritize targeting whoever just shot us!
			_target = attacker;
		}
	}

	private bool HasLineOfSight( Component target )
	{
		if ( !target.IsValid() )
			return false;

		var targetPos = GetAimPosition( target );
		var trace = Scene.Trace.Ray( EyePosition, targetPos )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "playerclip", "movement" )
			.UseHitboxes()
			.Run();

		return trace.Hit && HitTarget( trace.GameObject, target );
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
	[Property] public float MinSpawnDistanceFromBots { get; set; } = 800f;

	private int _nextBotIndex;

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
		var bots = Bots.ToList();

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
		var bots = Bots.Where( x => x.Team == team ).ToList();

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

		botObject.Tags.Add( BotTag );
		botObject.Tags.Add( "removable" );

		var bot = botObject.Components.Get<LightweightCombatBot>( true );
		if ( bot.IsValid() )
		{
			bot.Team = team;
			bot.BotName = BotNames[index % BotNames.Length];
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