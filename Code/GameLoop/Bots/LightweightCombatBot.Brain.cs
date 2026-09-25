namespace Facepunch;

/// <summary>
/// How a combat bot finds and fights enemies, modelled on a trained soldier rather than an aimbot. It has to see an
/// enemy (inside its field of view) or hear them before it knows they're there, and it reacts after a human delay. Its
/// aim starts rough and settles while it holds on target, then opens up again with recoil, its own movement and a
/// moving target. Every bot has its own <see cref="Skill"/> and <see cref="Aggression"/>, so some are recruits and
/// some veterans, and some push while others hold angles.
/// </summary>
public sealed partial class LightweightCombatBot
{
	/// <summary> 0 = recruit, 1 = veteran. Scales reaction time, aim, recoil control, turning and strafing. </summary>
	[Property, Group( "Skill" ), Range( 0, 1 )] public float Skill { get; set; } = 0.5f;
	/// <summary> 0 = holds angles and waits for enemies to come, 1 = pushes to them. </summary>
	[Property, Group( "Skill" ), Range( 0, 1 )] public float Aggression { get; set; } = 0.5f;
	/// <summary> Roll <see cref="Skill"/> and <see cref="Aggression"/> on spawn. The bot manager sets them itself, keeping each name's roll. </summary>
	[Property, Group( "Skill" )] public bool RandomizePersonality { get; set; } = true;
	/// <summary> Multiplies every bot's aim error: raise it to make all bots miss more. </summary>
	[Property, Group( "Skill" )] public float AimErrorScale { get; set; } = 1f;
	/// <summary> Hardcore kills in one hit, so bots react a little slower there and players get a fair first shot. </summary>
	[Property, Group( "Skill" )] public float HardcoreReactionScale { get; set; } = 1.15f;

	/// <summary> Full width of the cone the bot notices enemies in. Just outside it, only close enemies are noticed (and more slowly). </summary>
	[Property, Group( "Perception" )] public float FieldOfView { get; set; } = 120f;
	/// <summary> How far away an unsuppressed gunshot gives the shooter's rough position away. </summary>
	[Property, Group( "Perception" )] public float HearingRange { get; set; } = 2500f;
	/// <summary> How far away a running enemy's footsteps are heard. </summary>
	[Property, Group( "Perception" )] public float FootstepHearingRange { get; set; } = 550f;
	/// <summary> How far a bot's callout of an enemy it has spotted carries to teammates. </summary>
	[Property, Group( "Perception" )] public float CalloutRange { get; set; } = 3000f;

	/// <summary> Where the bot is aiming, for everyone's animation. </summary>
	[Sync( SyncFlags.FromHost )] public Vector3 AimDirection { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsCrouching { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsReloading { get; private set; }
	/// <summary> Host only: lets other bots hear this one shooting. </summary>
	public TimeSince TimeSinceFired { get; private set; } = 999f;

	private const float PerceptionInterval = 0.2f;
	private const int MaxSightChecksPerScan = 5;

	private static readonly string[] BodyBones = { "spine_2", "head", "pelvis" };

	private float SettledAimError => MathX.Lerp( 3.2f, 0.9f, Skill ) * AimErrorScale;
	private float AcquireAimError => MathX.Lerp( 8f, 4f, Skill ) * AimErrorScale;
	private float AimSettleTime => MathX.Lerp( 0.7f, 0.3f, Skill );
	private float RecoilPerShot => MathX.Lerp( 0.6f, 0.25f, Skill );
	private float RecoilRecovery => MathX.Lerp( 4f, 8f, Skill );
	private float TrackingLag => MathX.Lerp( 0.14f, 0.05f, Skill );
	private float TurnSpeed => MathX.Lerp( 220f, 480f, Skill );
	private float StrafeChance => MathX.Lerp( 0.25f, 0.75f, Skill );

	private static bool IsHardcore => GameMode.ActiveHardcore || (GameMode.Instance.IsValid() && GameMode.Instance.Hardcore);
	private static bool IsObjectiveMode => GameMode.Instance?.Ident is "domination" or "hardpoint";

	private Component _target;
	private bool _targetVisible;
	private Vector3 _targetPoint;
	private Vector3 _lastSeenPosition;
	private Vector3 _lastSeenVelocity;
	private TimeSince _timeSinceTargetSeen;
	private TimeUntil _reactionEnds;
	private TimeSince _timeSinceOnTarget;
	private float _acquireError;
	private float _recoil;
	private float _targetAngularSpeed;

	private Vector3 _aimDirection;
	private Vector3 _idleLook;
	private TimeUntil _nextLookAround;
	private Vector3? _contact;
	private TimeSince _timeSinceContact;
	private TimeSince _timeSinceContactStarted;
	private TimeSince _timeSincePerception;
	private TimeSince _timeSinceCallout;

	private Vector3? _moveTarget;
	private Vector3? _searchPoint;
	private Vector3? _huntDestination;
	private TimeUntil _nextHuntPick;
	private Vector3? _patrolTarget;
	private TimeSince _timeSincePatrolPick;
	private TimeUntil _nextStrafe;
	private Vector3 _stuckCheckPosition;
	private TimeSince _timeSinceStuckCheck;
	private TimeUntil _nextDoorCheck;
	private TerrorTown.MapMover _door;
	private TimeUntil _doorGiveUp;

	private bool _weaponStatsRead;
	private float _cycleTime = 0.075f;
	private int _magazineSize = 30;
	private int _magazine;
	private TimeUntil _reloadEnds;
	private TimeUntil _nextShot;
	private int _burstRemaining;

	/// <summary> A skill roll: most bots are average, a few are recruits or veterans. </summary>
	public static float RollSkill() => MathX.Lerp( -0.1f, 1.1f, (Game.Random.Float() + Game.Random.Float()) * 0.5f ).Clamp( 0f, 1f );

	private void RollPersonality()
	{
		Skill = RollSkill();
		Aggression = Game.Random.Float( 0.15f, 0.95f );
	}

	private void Think()
	{
		ReadWeaponStats();
		Perceive();
		UpdateReload();
		UpdateAim();
		UpdateMovement();
		UpdateShooting();
		_recoil = MathF.Max( 0f, _recoil - RecoilRecovery * Time.Delta );
	}

	private void ResetCombatState()
	{
		ForgetTarget();
		_contact = null;
		_huntDestination = null;
		IsCrouching = false;
		HoldPosition();
	}

	/// <summary> The bot fires its weapon's real cyclic rate and magazine. </summary>
	private void ReadWeaponStats()
	{
		if ( _weaponStatsRead )
			return;

		_weaponStatsRead = true;
		var prefab = WeaponResource?.MainPrefab;
		var shootable = prefab.IsValid() ? prefab.GetComponentInChildren<Shootable>( true ) : null;
		var ammo = prefab.IsValid() ? prefab.GetComponentInChildren<WeaponAmmo>( true ) : null;
		if ( shootable.IsValid() && shootable.FireRate > 0f )
			_cycleTime = 60f / shootable.FireRate;
		_magazineSize = Math.Max( 1, ammo?.MaxAmmo ?? 30 );
		_magazine = _magazineSize;
	}

	#region Perception

	private void Perceive()
	{
		if ( _timeSincePerception < PerceptionInterval )
			return;

		_timeSincePerception = 0f;

		if ( _target.IsValid() && !IsEnemyAlive( _target ) )
			ForgetTarget();

		// While we're already watching someone there's no field-of-view check: we're looking at them.
		if ( _targetVisible && TryFindVisiblePoint( _target, out var point ) )
		{
			UpdateSighting( _target, point );
		}
		else
		{
			_targetVisible = false;
			if ( FindVisibleEnemy( out var enemy, out var enemyPoint, out var peripheral ) )
				Acquire( enemy, enemyPoint, peripheral );
		}

		if ( _target.IsValid() && !_targetVisible && _timeSinceTargetSeen > TargetMemorySeconds )
			ForgetTarget();

		if ( !_targetVisible )
			Listen();
	}

	private IEnumerable<Component> Enemies()
	{
		foreach ( var bot in GameUtils.LightweightBots )
		{
			if ( bot != this && IsEnemyAlive( bot ) )
				yield return bot;
		}

		foreach ( var player in GameUtils.PlayerPawns )
		{
			if ( IsEnemyAlive( player ) )
				yield return player;
		}
	}

	private bool FindVisibleEnemy( out Component enemy, out Vector3 point, out bool peripheral )
	{
		point = default;
		peripheral = false;
		var checks = 0;
		var facing = _aimDirection.WithZ( 0f );
		if ( facing.IsNearZeroLength )
			facing = WorldRotation.Forward;

		foreach ( var candidate in Enemies().OrderBy( x => x.WorldPosition.DistanceSquared( WorldPosition ) ) )
		{
			var toCandidate = (candidate.WorldPosition - WorldPosition).WithZ( 0f );
			var distance = toCandidate.Length;
			if ( distance > SightRange )
				continue;

			// Behind us is invisible; the corner of the eye only catches someone close.
			var angle = distance < 1f ? 0f : Vector3.GetAngle( facing, toCandidate );
			if ( angle > 100f || (angle > FieldOfView * 0.5f && distance > 700f) )
				continue;

			if ( !Noticed( candidate, distance ) )
				continue;

			if ( checks++ >= MaxSightChecksPerScan )
				break;

			if ( TryFindVisiblePoint( candidate, out point ) )
			{
				enemy = candidate;
				peripheral = angle > FieldOfView * 0.5f;
				return true;
			}
		}

		enemy = null;
		return false;
	}

	/// <summary>
	/// Up close anyone in view is seen. Far away, a still or low enemy takes a few looks to pick out, so this is a
	/// chance per scan that grows if they move or shoot.
	/// </summary>
	private bool Noticed( Component target, float distance )
	{
		if ( distance < 1500f )
			return true;

		var chance = 1f - (distance - 1500f) / 3000f;
		if ( GetVelocity( target ).WithZ( 0f ).Length > 150f || FiredRecently( target, 0.5f ) )
			chance *= 2f;
		if ( IsLowProfile( target ) )
			chance *= 0.5f;
		chance *= MathX.Lerp( 0.7f, 1.2f, Skill );

		return Game.Random.Float() < chance.Clamp( 0.1f, 1f );
	}

	/// <summary> Any part of the target we can see, chest first since that's where a soldier aims. </summary>
	private bool TryFindVisiblePoint( Component target, out Vector3 point )
	{
		if ( target.IsValid() && target.WorldPosition.DistanceSquared( WorldPosition ) < SightRange * SightRange )
		{
			for ( var part = 0; part < BodyBones.Length; part++ )
			{
				point = GetBodyPoint( target, part );
				if ( CanSeePoint( target, point ) )
					return true;
			}
		}

		point = default;
		return false;
	}

	private bool CanSeePoint( Component target, Vector3 point )
	{
		// Run a little past the point so the ray enters the hitbox around it.
		var direction = (point - EyePosition).Normal;
		var trace = Scene.Trace.Ray( EyePosition, point + direction * 12f )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "playerclip", "movement" )
			.UseHitboxes()
			.Run();

		return trace.Hit && HitTarget( trace.GameObject, target );
	}

	/// <summary> Chest, head or pelvis, from the skeleton when it's available and from the stance otherwise. </summary>
	private static Vector3 GetBodyPoint( Component target, int part )
	{
		var renderer = target switch
		{
			PlayerPawn player => player.BodyRenderer,
			LightweightCombatBot bot => bot.Renderer,
			_ => null
		};

		if ( renderer.IsValid() && renderer.TryGetBoneTransform( BodyBones[part], out var bone )
			&& bone.Position.DistanceSquared( target.WorldPosition ) < 100f * 100f )
			return bone.Position;

		var eyeHeight = target switch
		{
			PlayerPawn { IsProne: true } => 24f,
			PlayerPawn { IsCrouching: true } => 48f,
			LightweightCombatBot { IsCrouching: true } => 44f,
			_ => 64f
		};

		var fraction = part switch { 1 => 1f, 0 => 0.72f, _ => 0.5f };
		return target.WorldPosition + Vector3.Up * (eyeHeight * fraction);
	}

	private void Acquire( Component enemy, Vector3 point, bool peripheral )
	{
		var toPoint = point - EyePosition;
		// Already looking where they appeared (holding the angle, or turned toward a noise), or they only just
		// ducked out of sight: quicker to react and closer to on target.
		var preAimed = Vector3.GetAngle( _aimDirection, toPoint ) < 15f;
		var reacquired = enemy == _target && _timeSinceTargetSeen < 3f;

		var reaction = MathX.Lerp( 0.75f, 0.25f, Skill ) * Game.Random.Float( 0.85f, 1.2f ) + toPoint.Length / 10000f;
		if ( peripheral ) reaction *= 1.5f;
		if ( preAimed || reacquired ) reaction *= 0.6f;
		if ( IsHardcore ) reaction *= HardcoreReactionScale;

		_target = enemy;
		_targetVisible = true;
		_reactionEnds = reaction;
		_acquireError = AcquireAimError * (preAimed ? 0.5f : 1f);
		_timeSinceOnTarget = 0f;
		_burstRemaining = 0;
		_searchPoint = null;
		_contact = null;
		UpdateSighting( enemy, point );
		CallOut( enemy );
	}

	private void UpdateSighting( Component enemy, Vector3 point )
	{
		_targetPoint = point;
		_lastSeenPosition = enemy.WorldPosition;
		_lastSeenVelocity = GetVelocity( enemy );
		_timeSinceTargetSeen = 0f;

		// How fast they cross our view; tracking lags behind that.
		var toTarget = point - EyePosition;
		var direction = toTarget.Normal;
		var lateral = _lastSeenVelocity - direction * _lastSeenVelocity.Dot( direction );
		_targetAngularSpeed = (lateral.Length / MathF.Max( toTarget.Length, 1f )).RadianToDegree();
	}

	/// <summary> The visible body point, following the target between scans. </summary>
	private Vector3 LiveTargetPoint => _targetVisible && _target.IsValid()
		? _targetPoint + (_target.WorldPosition - _lastSeenPosition)
		: _targetPoint;

	private void ForgetTarget()
	{
		_target = null;
		_targetVisible = false;
		_burstRemaining = 0;
		_searchPoint = null;
	}

	/// <summary> Gunfire gives away roughly where the shooter is, and so do running footsteps up close. </summary>
	private void Listen()
	{
		foreach ( var enemy in Enemies() )
		{
			var distance = enemy.WorldPosition.Distance( WorldPosition );
			var heard = (distance < HearingRange && FiredRecently( enemy, 0.3f ))
				|| (distance < FootstepHearingRange && IsNoisy( enemy ));
			if ( !heard )
				continue;

			// The direction of a sound is easy to place, its distance much less so.
			SetContact( enemy.WorldPosition + Vector3.Random.WithZ( 0f ) * distance * 0.15f );
			return;
		}
	}

	private void SetContact( Vector3 position )
	{
		// Repeated noise from the same place only refreshes the contact, so the bot doesn't re-path every scan.
		var refresh = _contact.HasValue && _timeSinceContact < 1.5f
			&& _contact.Value.DistanceSquared( position ) < 400f * 400f;
		_timeSinceContact = 0f;
		if ( refresh )
			return;

		_contact = position;
		_timeSinceContactStarted = 0f;
	}

	/// <summary> Tell nearby teammates where an enemy is, like a callout. </summary>
	private void CallOut( Component enemy )
	{
		if ( GameUtils.IsFreeForAllMode || _timeSinceCallout < 2f )
			return;

		_timeSinceCallout = 0f;
		foreach ( var mate in GameUtils.GetLightweightBots( Team ) )
		{
			if ( mate != this && mate.IsAlive && mate.WorldPosition.DistanceSquared( WorldPosition ) < CalloutRange * CalloutRange )
				mate.HearCallout( enemy.WorldPosition );
		}
	}

	private void HearCallout( Vector3 position )
	{
		if ( _targetVisible || (_contact.HasValue && _timeSinceContact < 3f) )
			return;

		SetContact( position + Vector3.Random.WithZ( 0f ) * 200f );
	}

	/// <summary> Being hit gives away roughly where the shooter is: turn to deal with them. </summary>
	private void OnShotBy( Component attacker )
	{
		if ( _targetVisible )
			return;

		_target = attacker;
		_lastSeenPosition = attacker.WorldPosition;
		_lastSeenVelocity = Vector3.Zero;
		_timeSinceTargetSeen = 0f;
		_searchPoint = null;
	}

	private static Vector3 GetVelocity( Component target ) => target switch
	{
		PlayerPawn player => player.CharacterController.IsValid() ? player.CharacterController.Velocity : player.SyncedVelocity,
		LightweightCombatBot bot => bot.Agent.IsValid() ? bot.Agent.Velocity : Vector3.Zero,
		_ => Vector3.Zero
	};

	private static bool FiredRecently( Component target, float seconds ) => target switch
	{
		PlayerPawn player => player.TimeSinceUnsuppressedShot < seconds,
		LightweightCombatBot bot => bot.TimeSinceFired < seconds,
		_ => false
	};

	private static bool IsLowProfile( Component target ) => target switch
	{
		PlayerPawn player => player.IsCrouching || player.IsProne,
		LightweightCombatBot bot => bot.IsCrouching,
		_ => false
	};

	private static bool IsNoisy( Component target )
	{
		var speed = GetVelocity( target ).WithZ( 0f ).Length;
		return target switch
		{
			PlayerPawn player => player.IsSprinting || (speed > 180f && !player.IsSlowWalking && !player.IsCrouching && !player.IsProne),
			LightweightCombatBot => speed > 150f,
			_ => false
		};
	}

	#endregion

	#region Aim

	private void UpdateAim()
	{
		if ( _aimDirection.IsNearZeroLength )
			_aimDirection = WorldRotation.Forward;

		var wanted = DesiredAimDirection();
		var angle = Vector3.GetAngle( _aimDirection, wanted );
		var step = TurnSpeed * Time.Delta;
		_aimDirection = angle <= step
			? wanted
			: Rotation.Slerp( Rotation.LookAt( _aimDirection ), Rotation.LookAt( wanted ), step / angle ).Forward;

		// The aim only settles while it's actually on them.
		if ( !_targetVisible || Vector3.GetAngle( _aimDirection, wanted ) > 6f )
			_timeSinceOnTarget = 0f;

		AimDirection = _aimDirection;

		var flat = _aimDirection.WithZ( 0f );
		if ( !flat.IsNearZeroLength )
			WorldRotation = Rotation.Lerp( WorldRotation, Rotation.LookAt( flat.Normal, Vector3.Up ), Time.Delta * 10f );
	}

	private Vector3 DesiredAimDirection()
	{
		if ( _targetVisible && _target.IsValid() )
			return (LiveTargetPoint - EyePosition).Normal;

		// Cover where the enemy was last seen, or where the noise came from, at chest height.
		if ( _target.IsValid() )
			return (_lastSeenPosition + Vector3.Up * 48f - EyePosition).Normal;
		if ( _contact.HasValue )
			return (_contact.Value + Vector3.Up * 48f - EyePosition).Normal;

		var velocity = Agent.IsValid() ? Agent.Velocity.WithZ( 0f ) : Vector3.Zero;
		if ( velocity.Length > 40f )
			return velocity.Normal;

		return LookAround();
	}

	/// <summary> Standing with nothing to go on, check the angles either side. </summary>
	private Vector3 LookAround()
	{
		if ( _nextLookAround.Relative <= 0f || _idleLook.IsNearZeroLength )
		{
			_nextLookAround = Game.Random.Float( 1.5f, 3.5f );
			_idleLook = (Rotation.LookAt( WorldRotation.Forward.WithZ( 0f ) ) * Rotation.FromYaw( Game.Random.Float( -70f, 70f ) )).Forward;
		}

		return _idleLook;
	}

	/// <summary> Radius in degrees of the cone the next round goes into. </summary>
	private float AimError()
	{
		var error = SettledAimError + _acquireError * MathF.Exp( -_timeSinceOnTarget / AimSettleTime ) + _recoil;

		var speed = Agent.IsValid() ? Agent.Velocity.WithZ( 0f ).Length : 0f;
		error *= 1f + 0.8f * (speed / MathF.Max( MoveSpeed, 1f )).Clamp( 0f, 1f );
		if ( IsCrouching )
			error *= 0.85f;

		return error + _targetAngularSpeed * TrackingLag;
	}

	#endregion

	#region Movement

	private void UpdateMovement()
	{
		if ( !Agent.IsValid() )
			return;

		CheckStuck();

		if ( WaitForDoor() )
			return;

		if ( _targetVisible && _target.IsValid() )
		{
			Engage();
			return;
		}

		IsCrouching = false;

		if ( _target.IsValid() )
			Search();
		else if ( _contact.HasValue && _timeSinceContact < 12f )
			Investigate();
		else if ( IsObjectiveMode )
			Patrol();
		else
			Hunt();
	}

	private void Engage()
	{
		// Until they've registered the enemy, carry on with whatever they were doing.
		if ( _reactionEnds.Relative > 0f )
			return;

		var toTarget = (_target.WorldPosition - WorldPosition).WithZ( 0f );
		var distance = toTarget.Length;
		// Aggressive bots fight closer.
		var wanted = PreferredRange * MathX.Lerp( 1.5f, 0.6f, Aggression );

		if ( IsReloading )
		{
			// Get small while the magazine goes in.
			IsCrouching = Aggression < 0.6f;
			HoldPosition();
			return;
		}

		if ( distance > wanted * 1.4f )
		{
			// Close in at a walk so the gun stays on them.
			IsCrouching = false;
			GoTo( _target.WorldPosition, MoveSpeed * 0.6f );
			return;
		}

		if ( _nextStrafe.Relative > 0f )
			return;

		_nextStrafe = Game.Random.Float( 0.6f, 1.5f );

		if ( Game.Random.Float() < StrafeChance )
		{
			// Side-step across their aim, backing off a little if they're too close.
			var away = distance > 1f ? -toTarget / distance : Vector3.Zero;
			var side = Vector3.Cross( away, Vector3.Up ) * (Game.Random.Float() < 0.5f ? -1f : 1f);
			var offset = side * Game.Random.Float( 96f, 220f );
			if ( distance < wanted * 0.5f )
				offset += away * 120f;

			IsCrouching = false;
			GoTo( WorldPosition + offset, MoveSpeed * 0.55f );
		}
		else
		{
			// Stand and shoot, or crouch for a steadier shot at range.
			IsCrouching = distance > 600f && Game.Random.Float() < MathX.Lerp( 0.6f, 0.2f, Aggression );
			HoldPosition();
		}
	}

	/// <summary> Lost sight of the enemy: hold the angle for a moment, since most come back out where they went in, then push. </summary>
	private void Search()
	{
		if ( _timeSinceTargetSeen < MathX.Lerp( 3f, 0.5f, Aggression ) )
		{
			HoldPosition();
			return;
		}

		_searchPoint ??= NavPoint( _lastSeenPosition + _lastSeenVelocity.WithZ( 0f ) * 0.75f );
		GoTo( _searchPoint.Value, MoveSpeed * MathX.Lerp( 0.6f, 0.9f, Aggression ) );

		// Not there any more: carry on hunting from here.
		if ( WorldPosition.DistanceSquared( _searchPoint.Value ) < 96f * 96f )
			ForgetTarget();
	}

	/// <summary> Go and look where a noise or a callout came from. Cautious bots turn toward it and wait first. </summary>
	private void Investigate()
	{
		if ( _timeSinceContactStarted < MathX.Lerp( 2.5f, 0f, Aggression ) )
		{
			HoldPosition();
			return;
		}

		GoTo( _contact.Value, MoveSpeed * 0.85f );
		if ( WorldPosition.DistanceSquared( _contact.Value ) < 160f * 160f )
			_contact = null;
	}

	private void Hunt()
	{
		if ( !_huntDestination.HasValue || _nextHuntPick.Relative <= 0f
			|| WorldPosition.DistanceSquared( _huntDestination.Value ) < 128f * 128f )
		{
			_huntDestination = PickHuntDestination();
			_nextHuntPick = Game.Random.Float( 5f, 9f );
		}

		GoTo( _huntDestination.Value, MoveSpeed );
	}

	/// <summary>
	/// Somewhere near an enemy, as if the team had a rough idea where they are. Real players are favoured so the fight
	/// comes to them, and the guess tightens as the bot closes in.
	/// </summary>
	private Vector3 PickHuntDestination()
	{
		Component chosen = null;
		var total = 0f;
		foreach ( var enemy in Enemies() )
		{
			var weight = (enemy is PlayerPawn ? 2.5f : 1f) / (enemy.WorldPosition.Distance( WorldPosition ) + 600f);
			total += weight;
			if ( Game.Random.Float( 0f, total ) < weight )
				chosen = enemy;
		}

		if ( !chosen.IsValid() )
			return RandomPatrolPoint();

		var uncertainty = (chosen.WorldPosition.Distance( WorldPosition ) * 0.35f).Clamp( 200f, 900f );
		var direction = Vector3.Random.WithZ( 0f );
		if ( direction.IsNearZeroLength )
			direction = Vector3.Forward;

		return NavPoint( chosen.WorldPosition + direction.Normal * Game.Random.Float( 0f, uncertainty ) );
	}

	private void Patrol()
	{
		if ( !_patrolTarget.HasValue || _timeSincePatrolPick > 10f || WorldPosition.DistanceSquared( _patrolTarget.Value ) < 96f * 96f )
		{
			_timeSincePatrolPick = 0f;
			_patrolTarget = FindPatrolTarget();
		}

		GoTo( _patrolTarget.Value, MoveSpeed * 0.85f );
	}

	private Vector3 FindPatrolTarget()
	{
		// Hardpoint game mode integration: capture active hardpoint
		var activeHardpoints = Scene.GetAllComponents<HardpointZone>().ToList();
		if ( activeHardpoints.Count > 0 )
		{
			var targetZone = Game.Random.FromList( activeHardpoints );
			var offset = Vector3.Random.WithZ( 0 ).Normal * Game.Random.Float( 30f, 90f );
			return NavPoint( targetZone.WorldPosition + offset );
		}

		// Domination game mode integration: capture active flags
		var activeFlags = Scene.GetAllComponents<DominationFlag>().ToList();
		if ( activeFlags.Count > 0 )
		{
			// Go to a random uncapped/enemy flag to capture it, or defend one once they're all ours.
			var enemyFlags = activeFlags.Where( x => x.ControllingTeam != Team ).ToList();
			var targetFlag = Game.Random.FromList( enemyFlags.Count > 0 ? enemyFlags : activeFlags );
			var offset = Vector3.Random.WithZ( 0 ).Normal * Game.Random.Float( 30f, 90f );
			return NavPoint( targetFlag.WorldPosition + offset );
		}

		return RandomPatrolPoint();
	}

	private Vector3 RandomPatrolPoint()
	{
		var direction = Vector3.Random.WithZ( 0f );
		if ( direction.LengthSquared < 0.01f )
			direction = WorldRotation.Forward;

		return NavPoint( WorldPosition + direction.Normal * Game.Random.Float( PatrolRadius * 0.35f, PatrolRadius ) );
	}

	private void GoTo( Vector3 position, float speed )
	{
		Agent.MaxSpeed = speed;
		if ( _moveTarget.HasValue && _moveTarget.Value.DistanceSquared( position ) < 48f * 48f )
			return;

		_moveTarget = position;
		Agent.MoveTo( NavPoint( position ) );
	}

	private void HoldPosition()
	{
		if ( !_moveTarget.HasValue )
			return;

		_moveTarget = null;
		Agent?.Stop();
	}

	private Vector3 NavPoint( Vector3 position ) => Scene.NavMesh.GetClosestPoint( position ) ?? position;

	/// <summary>
	/// A shut door ahead: open it and wait until it's open enough to walk through, like a person would.
	/// </summary>
	private bool WaitForDoor()
	{
		if ( _door.IsValid() )
		{
			if ( _door.OpenAmount < TerrorTown.MapMover.OpenEnough && _doorGiveUp.Relative > 0f && _door.OpenForNpc( WorldPosition ) )
				return true;

			_door = null;
			return false;
		}

		if ( _nextDoorCheck.Relative > 0f )
			return false;

		_nextDoorCheck = 0.1f;
		var door = TerrorTown.MapMover.FindDoorAhead( Scene, WorldPosition, Agent.Velocity );
		if ( !door.IsValid() || !door.OpenForNpc( WorldPosition ) )
			return false;

		_door = door;
		_doorGiveUp = 3f;
		HoldPosition();
		return true;
	}

	/// <summary> Wedged on something: drop the plan and pick another. </summary>
	private void CheckStuck()
	{
		if ( _timeSinceStuckCheck < 2f )
			return;

		_timeSinceStuckCheck = 0f;
		var moved = WorldPosition.Distance( _stuckCheckPosition );
		_stuckCheckPosition = WorldPosition;
		if ( !_moveTarget.HasValue || moved > 24f || WorldPosition.DistanceSquared( _moveTarget.Value ) < 96f * 96f )
			return;

		_moveTarget = null;
		_huntDestination = null;
		_patrolTarget = null;
		if ( !_targetVisible )
		{
			ForgetTarget();
			_contact = null;
		}
	}

	#endregion

	#region Shooting

	private void UpdateShooting()
	{
		if ( IsReloading || !_targetVisible || !IsEnemyAlive( _target )
			|| _reactionEnds.Relative > 0f || _nextShot.Relative > 0f )
			return;

		var toPoint = LiveTargetPoint - EyePosition;
		var distance = toPoint.Length;
		// Still swinging onto them.
		if ( distance > EngageRange || Vector3.GetAngle( _aimDirection, toPoint ) > 8f )
			return;

		if ( _burstRemaining <= 0 )
			_burstRemaining = RollBurst( distance );

		FireShot( toPoint.Normal );
		_burstRemaining--;
		_nextShot = _burstRemaining > 0 ? _cycleTime : BurstPause( distance );
	}

	/// <summary> Long bursts up close, controlled pairs at mid range, aimed singles far out. </summary>
	private static int RollBurst( float distance )
	{
		if ( distance < 500f ) return Game.Random.Int( 3, 7 );
		if ( distance < 1300f ) return Game.Random.Int( 2, 4 );
		return Game.Random.Int( 1, 2 );
	}

	private float BurstPause( float distance ) =>
		MathX.Lerp( 0.55f, 0.22f, Skill ) * Game.Random.Float( 0.8f, 1.3f ) + (distance > 1300f ? 0.15f : 0f);

	private void FireShot( Vector3 direction )
	{
		// A random point in the error cone, with recoil walking the muzzle up.
		var error = AimError();
		var angle = Game.Random.Float( 0f, MathF.PI * 2f );
		var radius = error * MathF.Sqrt( Game.Random.Float() );
		var spread = Rotation.From( radius * MathF.Sin( angle ) - _recoil * 0.4f, radius * MathF.Cos( angle ), 0f );
		var shotDirection = (Rotation.LookAt( direction ) * spread).Forward;

		var trace = Scene.Trace.Ray( EyePosition, EyePosition + shotDirection * (EngageRange + 1000f) )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "playerclip", "movement" )
			.UseHitboxes()
			.Run();

		_magazine--;
		_recoil += RecoilPerShot;
		TimeSinceFired = 0f;
		// Send the firing weapon's ammo choice with the shot so every observer sees the same effect.
		DoShootEffects( GetMuzzlePosition(), trace.EndPosition, UsesTracerRounds );

		if ( trace.Hit )
			ApplyHit( trace, shotDirection );
	}

	/// <summary> Whoever hostile the round hits takes it, not only the enemy being aimed at. </summary>
	private void ApplyHit( SceneTraceResult trace, Vector3 direction )
	{
		var victim = HitTarget( trace.GameObject, _target ) ? _target : Enemies().FirstOrDefault( x => HitTarget( trace.GameObject, x ) );
		if ( !IsEnemyAlive( victim ) )
			return;

		var hitbox = trace.GetHitboxTags();
		if ( hitbox == HitboxTags.None )
			hitbox = HitboxTags.Chest;

		var damage = victim is PlayerPawn ? Damage * RealPlayerDamageScale : Damage;
		var damageInfo = new DamageInfo( this, damage, this, trace.EndPosition, direction * damage, hitbox );

		switch ( victim )
		{
			case PlayerPawn player when player.HealthComponent.IsValid():
				player.HealthComponent.TakeDamage( damageInfo );
				break;
			case LightweightCombatBot bot when bot.HealthComponent.IsValid():
				bot.HealthComponent.TakeDamage( damageInfo );
				break;
		}
	}

	private void UpdateReload()
	{
		if ( IsReloading )
		{
			if ( _reloadEnds.Relative > 0f )
				return;

			IsReloading = false;
			_magazine = _magazineSize;
			return;
		}

		// Top up between fights rather than running dry in the next one.
		if ( _magazine <= 0 || (!_targetVisible && _timeSinceTargetSeen > 2f && _magazine < _magazineSize / 2) )
		{
			IsReloading = true;
			_burstRemaining = 0;
			_reloadEnds = MathX.Lerp( 2.9f, 2.1f, Skill ) * Game.Random.Float( 0.9f, 1.1f );
			PlayReloadAnimation();
		}
	}

	[Rpc.Broadcast]
	private void PlayReloadAnimation()
	{
		Renderer?.Set( "b_reload", true );
	}

	#endregion
}
