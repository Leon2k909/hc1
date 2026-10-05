namespace Facepunch;

/// <summary>
/// How a combat bot finds and fights enemies, modelled on a trained soldier rather than an aimbot. It has to see an
/// enemy (inside its field of view) or hear them before it knows they're there, and it reacts after a human delay. Its
/// aim starts rough and settles while it holds on target, then opens up again with recoil, its own movement and a
/// moving target. Every bot has its own <see cref="Skill"/> and its own way of fighting (<see cref="Habits"/>, with its
/// <see cref="BotStyle"/>), so some are recruits and some veterans, and some rush while others flank, hold angles or
/// pick people off from range.
/// </summary>
public sealed partial class LightweightCombatBot
{
	/// <summary> 0 = recruit, 1 = veteran. Scales reaction time, aim, recoil control, turning and strafing. </summary>
	[Property, Group( "Skill" ), Range( 0, 1 )] public float Skill { get; set; } = 0.5f;
	/// <summary> 0 = holds angles and waits for enemies to come, 1 = pushes to them. Comes with its <see cref="Habits"/>. </summary>
	[Property, Group( "Skill" ), Range( 0, 1 )] public float Aggression { get; set; } = 0.5f;
	/// <summary> Roll <see cref="Skill"/> and <see cref="Habits"/> on spawn. The bot manager sets them itself, keeping each name's roll. </summary>
	[Property, Group( "Skill" )] public bool RandomizePersonality { get; set; } = true;
	/// <summary> Multiplies every bot's aim error: raise it to make all bots miss more. </summary>
	[Property, Group( "Skill" )] public float AimErrorScale { get; set; } = 1f;
	/// <summary> Hardcore kills in one hit, so bots react a little slower there and players get a fair first shot. </summary>
	[Property, Group( "Skill" )] public float HardcoreReactionScale { get; set; } = 1.15f;
	/// <summary>
	/// A real player's bot teammates are there to support them, not to win the match for them: against enemy bots their
	/// aim error is multiplied by this, so the player gets most of the kills.
	/// </summary>
	[Property, Group( "Skill" )] public float SupportAimErrorScale { get; set; } = 2.5f;
	/// <summary> Likewise, a real player's bot teammates react this much slower to enemy bots. </summary>
	[Property, Group( "Skill" )] public float SupportReactionScale { get; set; } = 1.5f;

	/// <summary>
	/// Full width of the cone the bot notices enemies in. Just outside it, only close enemies are noticed (and more
	/// slowly). Narrower at a sprint (<see cref="SprintFieldOfView"/>).
	/// </summary>
	[Property, Group( "Perception" )] public float FieldOfView { get; set; } = 120f;
	/// <summary> How far away an unsuppressed gunshot gives the shooter's rough position away. </summary>
	[Property, Group( "Perception" )] public float HearingRange { get; set; } = 2500f;
	/// <summary>
	/// How far away a suppressed gunshot gives the shooter away (~20 m). It's still a loud crack, but it takes 25-30 dB
	/// off the blast, and far off the bullet's own crack downrange is easier to hear than where it came from.
	/// </summary>
	[Property, Group( "Perception" )] public float SuppressedHearingRange { get; set; } = 800f;
	/// <summary> How far away a running enemy's footsteps are heard: half as far through a wall, and not over the bot's own sprint. </summary>
	[Property, Group( "Perception" )] public float FootstepHearingRange { get; set; } = 550f;
	/// <summary> How far a bot's callout of an enemy it has spotted carries to teammates. </summary>
	[Property, Group( "Perception" )] public float CalloutRange { get; set; } = 3000f;

	/// <summary>
	/// The fight is where the real players are. Further than this from all of them, bots don't chase each other or go
	/// after noises, they keep heading for the players, so there are no side fights out in the distance.
	/// </summary>
	[Property, Group( "Movement" )] public float ActionRadius { get; set; } = 2500f;

	/// <summary> Where the bot is aiming, for everyone's animation. </summary>
	[Sync( SyncFlags.FromHost )] public Vector3 AimDirection { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsCrouching { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsReloading { get; private set; }
	/// <summary>
	/// In a fight, for everyone's animation: the gun comes up to the shoulder (<see cref="UpdateRightHandIk"/>) from
	/// spotting an enemy until <see cref="ShoulderedAfterSighting"/> after losing sight of them. Not while reloading.
	/// </summary>
	[Sync( SyncFlags.FromHost )] public bool IsAimingIn { get; private set; }
	/// <summary> Host only: lets other bots hear this one shooting. </summary>
	public TimeSince TimeSinceFired { get; private set; } = 999f;

	private const float PerceptionInterval = 0.2f;
	private const int MaxSightChecksPerScan = 5;
	private const int MaxWatchCorners = 6;
	/// <summary>
	/// The gap soldiers keep, about 5 m, so one burst or grenade can't catch several: what a bot leaves to the teammate
	/// in front on the move (<see cref="KeepInterval"/>), and between its spot and theirs (<see cref="PickFreeSpot"/>).
	/// </summary>
	private const float Interval = 200f;
	/// <summary> How far off a noise, a callout or a last sighting a bot takes its own spot when a teammate has that one. </summary>
	private const float SpotSpread = 500f;
	/// <summary>
	/// Real players are what the bots are here for: picking whom to shoot or which shot to go after, a real player counts
	/// as this share of their distance, so one twice as far off as a bot still comes first.
	/// </summary>
	private const float PlayerPriority = 0.5f;
	/// <summary>
	/// Gunfire from a fight between bots draws a bot only from this share of <see cref="HearingRange"/>. Further off it
	/// says where a fight is, not that it's this bot's, and every bot within earshot heading for it bunched them all up
	/// there. A real player's shots draw them from the whole of it.
	/// </summary>
	private const float BotGunfireDraw = 0.5f;
	/// <summary>
	/// A callout about a bot reaches only this many of the nearest teammates, a fire team, rather than the whole team.
	/// A callout about a real player reaches everyone in <see cref="CalloutRange"/>.
	/// </summary>
	private const int FireTeamSize = 2;
	/// <summary> Other spots tried around a place before settling for the least crowded. </summary>
	private const int SpotTries = 5;
	/// <summary>
	/// How far along its route a bot on the move looks (<see cref="RouteAhead"/>): about 0.7 s at a run, so it turns into
	/// a corner over the last few strides before it, the way a person looks round a bend before taking it.
	/// </summary>
	private const float RouteLookAhead = 160f;
	/// <summary>
	/// A player's gaits with a gun out (PlayerGlobals' defaults, as <see cref="Gunsmith.GunsmithStats"/> reads them): a
	/// walk at 220 and a sprint at 260, less the gun's SpeedPenalty (all of it walking, half of it sprinting), and slower
	/// again for a heavy gun. A bot walks and sprints at the speeds a player would with its gun (<see cref="ReadGaits"/>).
	/// </summary>
	private const float PlayerWalkSpeed = 220f;
	private const float PlayerSprintSpeed = 260f;
	/// <summary>
	/// A player can't fire while sprinting or for this long after (PlayerPawn's "no_shooting" tag), while the gun comes
	/// up, and nor can a bot. So one caught at a run pays for it.
	/// </summary>
	private const float SprintOutTime = 0.25f;
	/// <summary>
	/// Full width of the cone a sprinting bot notices enemies in (<see cref="FieldOfView"/> otherwise): at a run a person
	/// watches where they're going.
	/// </summary>
	private const float SprintFieldOfView = 90f;

	private static readonly string[] BodyBones = { "spine_2", "head", "pelvis" };

	private float SettledAimError => MathX.Lerp( 3.2f, 0.9f, Skill ) * AimErrorScale;
	private float AcquireAimError => MathX.Lerp( 8f, 4f, Skill ) * AimErrorScale;
	private float AimSettleTime => MathX.Lerp( 0.7f, 0.3f, Skill );
	private float RecoilPerShot => MathX.Lerp( 0.6f, 0.25f, Skill );
	private float RecoilRecovery => MathX.Lerp( 4f, 8f, Skill );
	private float TrackingLag => MathX.Lerp( 0.14f, 0.05f, Skill );
	private float TurnSpeed => MathX.Lerp( 220f, 480f, Skill );

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
	private Vector3? _contactSpot;
	private bool _contactUnreachable;
	private TimeSince _timeSinceContact;
	private TimeSince _timeSinceContactStarted;
	private Vector3? _watchPoint;
	/// <summary> <see cref="_watchPoint"/> came from the route to the threat, worked out from here, to there, then. </summary>
	private bool _watchRouted;
	private Vector3 _watchRouteFrom;
	private Vector3 _watchRouteThreat;
	private TimeSince _timeSinceWatchRoute;
	private TimeSince _timeSincePerception;
	private TimeSince _timeSinceCallout;

	private Vector3? _moveTarget;
	private Vector3? _searchPoint;
	/// <summary> Where the bot is closing in on its target to (<see cref="EngageSpot"/>), and where they were then. </summary>
	private Vector3? _engageSpot;
	private Vector3 _engageSpotFor;
	private Vector3? _huntDestination;
	private TimeUntil _nextHuntPick;
	/// <summary> The enemy <see cref="_huntDestination"/> is a guess at; null while roaming. </summary>
	private Component _huntTarget;
	/// <summary> Where the guess put them, level from where they were, and how far out the guess could be then. </summary>
	private Vector3 _huntGuess;
	private float _huntUncertainty;
	private TimeUntil _nextHuntTargetPick;
	private Vector3? _patrolTarget;
	private TimeSince _timeSincePatrolPick;
	private Vector3 _stuckCheckPosition;
	private TimeSince _timeSinceStuckCheck;
	private Vector3? _unreachable;
	private TimeSince _timeSinceUnreachable;
	private TimeUntil _nextDoorCheck;
	private TerrorTown.MapMover _door;
	private TimeUntil _doorGiveUp;
	private TimeUntil _playerInTheWay;

	private bool _weaponStatsRead;
	private float _cycleTime = 0.075f;
	private int _magazineSize = 30;
	private int _magazine;
	private float _roundDamage;
	private Curve _damageFalloff;
	private float _maxRange;
	private float _reloadTime = 1.5f;
	private float _emptyReloadTime = 2f;
	private TimeUntil _reloadEnds;
	private TimeUntil _nextShot;
	private int _burstRemaining;
	/// <summary> Between the rounds of the string being fired: the cyclic rate in a burst, a trigger press in a pair. </summary>
	private float _splitTime;
	/// <summary> The gun's fire modes: automatic, semi, and a burst mode's length (0 without one, as on most). </summary>
	private bool _hasAutomatic = true;
	private bool _hasSemi = true;
	private int _burstLength;
	/// <summary> An LMG: the fire team's automatic rifleman, who fires bursts at every range (<see cref="RollString"/>). </summary>
	private bool _isMachineGunner;
	private bool _isSubmachineGun;
	/// <summary> A player's walk and sprint with this gun out (<see cref="ReadGaits"/>); zero until read. </summary>
	private float _walkSpeed;
	private float _sprintSpeed;
	/// <summary> Host: since the bot last moved faster than a walk (<see cref="IsSprinting"/>). </summary>
	private TimeSince _timeSinceSprinting = 999f;
	/// <summary> A teammate's callout on its way (<see cref="HearCallout"/>): where they said, and when it's taken in. </summary>
	private Vector3? _callout;
	private TimeUntil _calloutHeard;

	/// <summary>
	/// A skill roll: most bots are average, a few are recruits or veterans. A custom game can set their difficulty
	/// (CustomGameRules.BotDifficulty), which narrows the roll round that level.
	/// </summary>
	public static float RollSkill()
	{
		var (low, high) = CustomGameSettings.ActiveRules.BotDifficulty switch
		{
			BotDifficulty.Recruit => (0f, 0.3f),
			BotDifficulty.Regular => (0.3f, 0.6f),
			BotDifficulty.Hardened => (0.55f, 0.85f),
			BotDifficulty.Veteran => (0.8f, 1f),
			_ => (-0.1f, 1.1f)
		};

		return MathX.Lerp( low, high, (Game.Random.Float() + Game.Random.Float()) * 0.5f ).Clamp( 0f, 1f );
	}

	private void RollPersonality()
	{
		Skill = RollSkill();
		Habits = BotHabits.Roll( WeaponResource?.Category );
		Aggression = Habits.Aggression;
	}

	private void Think()
	{
		ReadWeaponStats();
		ReadGaits();
		if ( IsSprinting )
			_timeSinceSprinting = 0f;
		Perceive();
		UpdateReload();
		UpdateAim();
		UpdateMovement();
		UpdateShooting();
		_recoil = MathF.Max( 0f, _recoil - RecoilRecovery * Time.Delta );
		// The gun stays up a moment after they duck out of sight, covering where they went.
		IsAimingIn = !IsReloading && IsEnemyAlive( _target ) && (_targetVisible || _timeSinceTargetSeen < ShoulderedAfterSighting);
	}

	/// <summary> How long (s) the gun stays at the shoulder after the target is lost from sight. </summary>
	private const float ShoulderedAfterSighting = 2f;

	/// <summary>
	/// Host: moving faster than a walk, which only a sprint is. The gun is carried (<see cref="MaxShoulderedSpeed"/>) and
	/// can't fire until <see cref="SprintOutTime"/> after, and the bot sees and hears less round it.
	/// </summary>
	private bool IsSprinting => Agent.IsValid() && Agent.Velocity.WithZ( 0f ).Length > MaxShoulderedSpeed;

	private void ResetCombatState()
	{
		ForgetTarget();
		_contact = null;
		_callout = null;
		_huntDestination = null;
		_huntTarget = null;
		IsCrouching = false;
		IsAimingIn = false;
		HoldPosition();
	}

	/// <summary> The bot fires its weapon's real cyclic rate, magazine, damage and reload times. </summary>
	private void ReadWeaponStats()
	{
		if ( _weaponStatsRead )
			return;

		_weaponStatsRead = true;
		var prefab = WeaponResource?.MainPrefab;
		var shootable = WeaponShootable;
		var ammo = prefab.IsValid() ? prefab.GetComponentInChildren<WeaponAmmo>( true ) : null;
		var reloadable = prefab.IsValid() ? prefab.GetComponentInChildren<Reloadable>( true ) : null;
		// A suppressor's back-pressure speeds some actions up, as for a player (Shootable.SuppressorFireRateScale).
		if ( shootable.IsValid() && shootable.FireRate > 0f )
			_cycleTime = 60f / (shootable.FireRate * (IsSuppressed ? shootable.SuppressorFireRateScale : 1f));
		// What the gun can do sets how it's fired (RollString): the M16A4 has semi and a three-round burst, no automatic.
		if ( shootable.IsValid() && shootable.SupportedFireModes is { Count: > 0 } modes )
		{
			_hasAutomatic = modes.Contains( FireMode.Automatic );
			_hasSemi = modes.Contains( FireMode.Semi );
			_burstLength = modes.Contains( FireMode.Burst ) ? Math.Max( 1, shootable.BurstAmount ) : 0;
		}
		_isMachineGunner = WeaponResource?.Category == WeaponCategory.LMG;
		_isSubmachineGun = WeaponResource?.Category == WeaponCategory.SMG;
		_roundDamage = shootable.IsValid() ? shootable.BaseDamage : Damage;
		if ( shootable.IsValid() )
		{
			_damageFalloff = shootable.BaseDamageFalloff;
			_maxRange = shootable.MaxRange;
		}
		if ( reloadable.IsValid() )
		{
			_reloadTime = reloadable.ReloadTime;
			_emptyReloadTime = reloadable.EmptyReloadTime;
		}
		_magazineSize = Math.Max( 1, ammo?.MaxAmmo ?? 30 );
		_magazine = _magazineSize;
	}

	/// <summary>
	/// A player's walk and sprint with this gun out (PlayerPawn.Movement.GetWishSpeed), which the bot moves at too. The
	/// walk stays under the speed the gun is carried at, so a walking bot has it up.
	/// </summary>
	private void ReadGaits()
	{
		if ( _sprintSpeed > 0f )
			return;

		var prefab = WeaponResource?.MainPrefab;
		var equipment = prefab.IsValid() ? prefab.GetComponentInChildren<Equipment>( true ) : null;
		var penalty = equipment.IsValid() ? equipment.SpeedPenalty : 40f;
		var weight = 1f - (equipment.IsValid() ? equipment.WeightSlowdown : 0f);
		_walkSpeed = MathF.Min( (PlayerWalkSpeed - penalty) * weight, MaxShoulderedSpeed - 10f );
		_sprintSpeed = (PlayerSprintSpeed - penalty * 0.5f) * weight;
	}

	/// <summary> The round's damage after the gun's falloff, as a player's shot works it out (Shootable.CalculateDamageFalloff). </summary>
	private float RoundDamage( float distance ) =>
		_maxRange > 0f ? _roundDamage * _damageFalloff.Evaluate( distance / _maxRange ) : _roundDamage;

	#region Perception

	/// <summary>
	/// How often the bot looks and listens. Out where no player is, nobody sees the fight, so it looks less often and
	/// notices someone up to a third of a second later (<see cref="BotSystem.LodEnabled"/>).
	/// </summary>
	private float PerceptionIntervalNow
	{
		get
		{
			if ( !BotSystem.LodEnabled || BotSystem.Current is not { } system )
				return PerceptionInterval;

			var distance = system.DistanceToNearestViewer( WorldPosition );
			return distance < 3000f ? PerceptionInterval : distance < 8000f ? 0.3f : 0.5f;
		}
	}

	private void Perceive()
	{
		if ( _timeSincePerception < PerceptionIntervalNow )
			return;

		_timeSincePerception = 0f;

		if ( _target.IsValid() && !IsEnemyAlive( _target ) )
			ForgetTarget();

		// While we're already watching someone there's no field-of-view check: we're looking at them.
		if ( _targetVisible && TryFindVisiblePoint( _target, out var point ) )
		{
			UpdateSighting( _target, point );

			// In a fight with a bot, a real player coming into view takes over, unless they're more than twice as far off:
			// they're what the bots are here for (PlayerPriority). Turning to them takes a reaction like any new target.
			var within = _target.WorldPosition.Distance( WorldPosition ) / PlayerPriority;
			if ( !IsRealPlayer( _target ) && FindVisibleEnemy( out var player, out var playerPoint, out var aside, playersOnly: true, within ) )
				Acquire( player, playerPoint, aside );
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
		{
			TakeInCallout();
			Listen();
			UpdateWatchPoint();
		}
	}

	/// <summary> Every living bot, from this frame's <see cref="BotSystem"/> list (a scene search without one). </summary>
	private static List<LightweightCombatBot> LivingBots => BotSystem.Current?.AliveBots
		?? GameUtils.LightweightBots.Where( x => x.IsValid() && x.IsAlive ).ToList();

	/// <summary> Every living player pawn, likewise. </summary>
	private static List<PlayerPawn> LivingPawns => BotSystem.Current?.AlivePawns
		?? GameUtils.PlayerPawns.Where( x => x.HealthComponent.IsValid() && x.HealthComponent.State == LifeState.Alive ).ToList();

	/// <summary> The living pawns of real people (not bot clients): where the action is. </summary>
	private static List<PlayerPawn> LivingPlayers => BotSystem.Current?.AlivePlayers
		?? LivingPawns.Where( IsRealPlayer ).ToList();

	/// <summary> A real person's pawn, not a bot's. </summary>
	private static bool IsRealPlayer( Component target ) =>
		target is PlayerPawn player && (!player.Client.IsValid() || !player.Client.IsBot);

	/// <summary> The bots and players this bot would shoot, added to <paramref name="into"/>. </summary>
	private void CollectEnemies( List<Component> into )
	{
		foreach ( var bot in LivingBots )
		{
			if ( bot != this && IsEnemyAlive( bot ) )
				into.Add( bot );
		}

		foreach ( var player in LivingPawns )
		{
			if ( IsEnemyAlive( player ) )
				into.Add( player );
		}
	}

	/// <summary> Scratch lists for thinking: bots think one at a time on the main thread, so they can share them. </summary>
	private static readonly List<Component> EnemyScratch = new();
	private static readonly List<Vector3> SpotScratch = new();
	private static float[] _sortKeys = new float[64];
	private static Component[] _sortItems = new Component[64];

	/// <summary>
	/// The enemy the bot notices first, out to sight range (and <paramref name="within"/>): the nearest, with a real
	/// player counting as <see cref="PlayerPriority"/> of their distance. Only real players if <paramref name="playersOnly"/>.
	/// </summary>
	private bool FindVisibleEnemy( out Component enemy, out Vector3 point, out bool peripheral, bool playersOnly = false,
		float within = float.MaxValue )
	{
		EnemyScratch.Clear();
		CollectEnemies( EnemyScratch );
		var range = MathF.Min( SightRange, within );
		var count = 0;
		foreach ( var candidate in EnemyScratch )
		{
			var real = IsRealPlayer( candidate );
			if ( playersOnly && !real )
				continue;
			if ( (candidate.WorldPosition - WorldPosition).WithZ( 0f ).LengthSquared > range * range )
				continue;

			if ( count == _sortKeys.Length )
			{
				Array.Resize( ref _sortKeys, count * 2 );
				Array.Resize( ref _sortItems, count * 2 );
			}

			_sortKeys[count] = candidate.WorldPosition.DistanceSquared( WorldPosition ) * (real ? PlayerPriority * PlayerPriority : 1f);
			_sortItems[count++] = candidate;
		}

		EnemyScratch.Clear();
		Array.Sort( _sortKeys, _sortItems, 0, count );
		var found = FindVisibleAmongNearest( count, out enemy, out point, out peripheral );
		Array.Clear( _sortItems, 0, count );
		return found;
	}

	/// <summary> The first of the <paramref name="count"/> nearest enemies (sorted into _sortItems) the bot notices and can see. </summary>
	private bool FindVisibleAmongNearest( int count, out Component enemy, out Vector3 point, out bool peripheral )
	{
		point = default;
		peripheral = false;
		var checks = 0;
		var facing = _aimDirection.WithZ( 0f );
		if ( facing.IsNearZeroLength )
			facing = WorldRotation.Forward;
		// At a run a person watches where they're going: a narrower cone, and only someone closer at the corner of the eye.
		var sprinting = IsSprinting;
		var halfView = (sprinting ? SprintFieldOfView : FieldOfView) * 0.5f;
		var outerAngle = sprinting ? 80f : 100f;
		var cornerRange = sprinting ? 350f : 700f;

		for ( var i = 0; i < count; i++ )
		{
			var candidate = _sortItems[i];
			var toCandidate = (candidate.WorldPosition - WorldPosition).WithZ( 0f );
			var distance = toCandidate.Length;

			// Behind us is invisible; the corner of the eye only catches someone close.
			var angle = distance < 1f ? 0f : Vector3.GetAngle( facing, toCandidate );
			if ( angle > outerAngle || (angle > halfView && distance > cornerRange) )
				continue;

			if ( !Noticed( candidate, distance ) )
				continue;

			if ( checks++ >= MaxSightChecksPerScan )
				break;

			if ( TryFindVisiblePoint( candidate, out point ) )
			{
				enemy = candidate;
				peripheral = angle > halfView;
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
			.WithoutTags( "trigger", "playerclip", "movement", BreakableGlass.Tag )
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
		if ( IsSupporting( enemy ) ) reaction *= SupportReactionScale;

		_target = enemy;
		_targetVisible = true;
		_reactionEnds = reaction;
		_acquireError = AcquireAimError * (preAimed ? 0.5f : 1f);
		_timeSinceOnTarget = 0f;
		_burstRemaining = 0;
		_searchPoint = null;
		_engageSpot = null;
		_contact = null;
		_callout = null;
		// Its next move is picked as soon as it has registered them (Engage). Caught at a run, it lets the sprint go first
		// (SprintBreak).
		StartFight( reacquired );
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
		_engageSpot = null;
	}

	/// <summary>
	/// Gunfire gives away roughly where the shooter is, and so do running footsteps up close: through a wall only half as
	/// far, and not over the bot's own at a sprint. Heard through walls from further off, footsteps had bots facing the
	/// corner a player would come round before they came round it. Of everyone heard, the bot goes after the nearest, a
	/// real player counting as <see cref="PlayerPriority"/> of their distance, and a fight between bots only draws it from
	/// close by (<see cref="BotGunfireDraw"/>).
	/// </summary>
	private void Listen()
	{
		var sprinting = IsSprinting;
		EnemyScratch.Clear();
		CollectEnemies( EnemyScratch );
		Vector3? heardAt = null;
		var heardDistance = 0f;
		var best = float.MaxValue;
		foreach ( var enemy in EnemyScratch )
		{
			var real = IsRealPlayer( enemy );
			var distance = enemy.WorldPosition.Distance( WorldPosition );
			var heard = (distance < HearingRange * (real ? 1f : BotGunfireDraw) && FiredRecently( enemy, 0.3f ))
				|| (distance < SuppressedHearingRange && FiredSuppressedRecently( enemy, 0.3f ))
				|| (!sprinting && distance < FootstepHearingRange && IsNoisy( enemy )
					&& (distance < FootstepHearingRange * 0.5f || HasClearView( enemy.WorldPosition + Vector3.Up * 48f )));
			var key = distance * (real ? PlayerPriority : 1f);
			if ( !heard || key >= best || AwayFromAction( enemy.WorldPosition ) )
				continue;

			best = key;
			heardAt = enemy.WorldPosition;
			heardDistance = distance;
		}

		EnemyScratch.Clear();

		// The direction of a sound is easy to place, its distance much less so.
		if ( heardAt is { } position )
			SetContact( position + Vector3.Random.WithZ( 0f ) * heardDistance * 0.15f );
	}

	private void SetContact( Vector3 position )
	{
		// Repeated noise from the same place only refreshes the contact, so the bot doesn't re-path every scan.
		var samePlace = _contact.HasValue && _contact.Value.DistanceSquared( position ) < 400f * 400f;
		var refresh = samePlace && _timeSinceContact < 1.5f;
		_timeSinceContact = 0f;
		if ( refresh )
			return;

		// A threat somewhere else needs a new spot to close in on it from (see Investigate).
		if ( !samePlace )
			_contactSpot = null;
		_contact = position;
		_contactUnreachable = false;
		_timeSinceContactStarted = 0f;
	}

	/// <summary>
	/// Where to look for a threat the bot can't see (where the enemy was last seen, a noise or a callout): straight at it
	/// if nothing's in the way, otherwise as far along the way there as the bot can see, which is where they'd come from,
	/// like a soldier covering a doorway and the corridor past it. Staring at them through the wall looked like a wallhack.
	/// </summary>
	private void UpdateWatchPoint( bool rerouteNow = false )
	{
		var threat = _target.IsValid() ? _lastSeenPosition : _contact;
		if ( !threat.HasValue )
		{
			_watchPoint = null;
			_watchRouted = false;
			return;
		}

		var chest = Vector3.Up * 48f;
		if ( HasClearView( threat.Value + chest ) )
		{
			_watchPoint = threat.Value + chest;
			_watchRouted = false;
			return;
		}

		// The way there hardly changes while neither the bot nor the threat has moved much, so keep the corner found
		// last time for a second rather than searching the navmesh again every scan.
		if ( !rerouteNow && _watchRouted && BotSystem.LodEnabled && _timeSinceWatchRoute < 1f
			&& _watchRouteThreat.DistanceSquared( threat.Value ) < 64f * 64f
			&& _watchRouteFrom.DistanceSquared( WorldPosition ) < 64f * 64f )
			return;

		_watchRouted = true;
		_watchRouteThreat = threat.Value;
		_watchRouteFrom = WorldPosition;
		_timeSinceWatchRoute = 0f;
		_watchPoint = null;

		var points = Scene.NavMesh.CalculatePath( new Sandbox.Navigation.CalculatePathRequest
		{
			Start = WorldPosition,
			Target = threat.Value
		} ).Points;
		if ( points is not { Count: > 1 } )
			return;

		// The last corner in view, then as far down the next leg as the bot can see.
		var corner = 0;
		while ( corner + 1 < points.Count && corner < MaxWatchCorners && HasClearView( points[corner + 1].Position + chest ) )
			corner++;

		if ( corner > 0 )
			_watchPoint = points[corner].Position + chest;
		if ( corner + 1 >= points.Count )
			return;

		var from = points[corner].Position;
		var leg = points[corner + 1].Position - from;
		var length = leg.Length;
		for ( var along = 32f; along < length; along *= 2f )
		{
			var point = from + leg * (along / length) + chest;
			if ( !HasClearView( point ) )
				break;

			_watchPoint = point;
		}

		// Nothing on the way in view (a shut door right in front, say): face the way there.
		_watchPoint ??= points[corner + 1].Position + chest;
	}

	/// <summary> Nothing solid between the bot's eyes and <paramref name="point"/>. People and window glass don't count. </summary>
	private bool HasClearView( Vector3 point ) => !Scene.Trace.Ray( EyePosition, point )
		.IgnoreGameObjectHierarchy( GameObject )
		.WithoutTags( "trigger", "playerclip", "movement", "player", LightweightBotManager.BotTag, BreakableGlass.Tag )
		.Run().Hit;

	/// <summary>
	/// Tell nearby teammates where an enemy is, like a callout: every teammate in range for a real player, only the
	/// nearest fire team (<see cref="FireTeamSize"/>) for a bot. Every sighting of a bot used to send the whole team.
	/// </summary>
	private void CallOut( Component enemy )
	{
		if ( GameUtils.IsFreeForAllMode || _timeSinceCallout < 2f )
			return;

		_timeSinceCallout = 0f;
		var mates = LivingBots.Where( mate => mate != this && mate.Team == Team
			&& mate.WorldPosition.DistanceSquared( WorldPosition ) < CalloutRange * CalloutRange );
		if ( !IsRealPlayer( enemy ) )
			mates = mates.OrderBy( mate => mate.WorldPosition.DistanceSquared( WorldPosition ) ).Take( FireTeamSize );

		foreach ( var mate in mates.ToList() )
			mate.HearCallout( enemy.WorldPosition );
	}

	/// <summary>
	/// A callout takes a moment to make and take in (0.8-2 s), and "by the red car" only puts them roughly there, the
	/// rougher the further off. Every teammate knowing at once, to within 200 units, where a bot had just seen someone had
	/// them all watching the right corner.
	/// </summary>
	private void HearCallout( Vector3 position )
	{
		if ( _targetVisible || (_contact.HasValue && _timeSinceContact < 3f) || _callout.HasValue || AwayFromAction( position ) )
			return;

		_callout = position;
		_calloutHeard = Game.Random.Float( 0.8f, 2f );
	}

	/// <summary> A callout on its way (<see cref="HearCallout"/>) becomes a contact once it's been taken in. </summary>
	private void TakeInCallout()
	{
		if ( _callout is not { } position || _calloutHeard.Relative > 0f )
			return;

		_callout = null;
		if ( _contact.HasValue && _timeSinceContact < 3f )
			return;

		SetContact( position + Vector3.Random.WithZ( 0f ) * (200f + position.Distance( WorldPosition ) * 0.1f) );
	}

	/// <summary> Being hit gives away roughly where the shooter is: turn to deal with them. </summary>
	private void OnShotBy( Component attacker )
	{
		// In a fight, most get off the spot they were hit on (Manoeuvre).
		_hurt = true;
		if ( _targetVisible )
			return;

		_target = attacker;
		_lastSeenPosition = attacker.WorldPosition;
		_lastSeenVelocity = Vector3.Zero;
		_timeSinceTargetSeen = 0f;
		_searchPoint = null;
		UpdateWatchPoint( rerouteNow: true );
	}

	private static Vector3 GetVelocity( Component target ) => target switch
	{
		PlayerPawn player => player.CharacterController.IsValid() ? player.CharacterController.Velocity : player.SyncedVelocity,
		LightweightCombatBot bot => bot.Agent.IsValid() ? bot.Agent.Velocity : Vector3.Zero,
		_ => Vector3.Zero
	};

	/// <summary> An unsuppressed shot from <paramref name="target"/> in the last <paramref name="seconds"/>. </summary>
	private static bool FiredRecently( Component target, float seconds ) => target switch
	{
		PlayerPawn player => player.TimeSinceUnsuppressedShot < seconds,
		LightweightCombatBot bot => !bot.IsSuppressed && bot.TimeSinceFired < seconds,
		_ => false
	};

	/// <summary> A suppressed shot from <paramref name="target"/> in the last <paramref name="seconds"/>. </summary>
	private static bool FiredSuppressedRecently( Component target, float seconds ) => target switch
	{
		PlayerPawn player => player.TimeSinceSuppressedShot < seconds,
		LightweightCombatBot bot => bot.IsSuppressed && bot.TimeSinceFired < seconds,
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

		// Cover where the enemy was last seen, or where the noise came from, or the corner they'd come round. Not at a
		// sprint: a runner looks where they're going.
		if ( (_target.IsValid() || _contact.HasValue) && _watchPoint.HasValue && !IsSprinting )
			return (_watchPoint.Value - EyePosition).Normal;

		// On the move, where the route goes, not where the bot's momentum is carrying it: facing its velocity, it turned
		// only as fast as that did, and looked off at random whenever a turn slowed it down.
		if ( RouteAhead() is { } ahead )
			return ahead;

		var velocity = Agent.IsValid() ? Agent.Velocity.WithZ( 0f ) : Vector3.Zero;
		if ( velocity.Length > 40f )
			return velocity.Normal;

		return LookAround();
	}

	/// <summary> Level, toward the point <see cref="RouteLookAhead"/> along the route; null when the bot isn't on one. </summary>
	private Vector3? RouteAhead()
	{
		if ( !Agent.IsValid() || !Agent.IsNavigating )
			return null;

		var ahead = (Agent.GetLookAhead( RouteLookAhead ) - Agent.AgentPosition).WithZ( 0f );
		return ahead.Length > 16f ? ahead.Normal : null;
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

		// Shooting on the move is harder, a veteran less so: so the holders stop for their aimed shots.
		var speed = Agent.IsValid() ? Agent.Velocity.WithZ( 0f ).Length : 0f;
		error *= 1f + MathX.Lerp( 0.9f, 0.55f, Skill ) * (speed / MathF.Max( MoveSpeed, 1f )).Clamp( 0f, 1f );
		if ( IsCrouching )
			error *= 0.85f;

		error += _targetAngularSpeed * TrackingLag;
		// Hardcore: a shot arm or hand can't hold the gun steady.
		if ( HealthComponent.IsValid() )
			error *= 1f + 0.4f * Math.Min( HealthComponent.ArmWounds, 2 );
		return IsSupporting( _target ) ? error * SupportAimErrorScale : error;
	}

	/// <summary> Is this bot on a real player's team, fighting an enemy bot? See <see cref="SupportAimErrorScale"/>. </summary>
	private bool IsSupporting( Component enemy ) =>
		enemy is LightweightCombatBot && !GameUtils.IsFreeForAllMode && Team != Team.Unassigned
		&& (BotSystem.Current?.TeamHasRealPlayer( Team ) ?? GameUtils.GetPlayers( Team ).Any( x => x.IsValid() && x.IsConnected && !x.IsBot ));

	#endregion

	#region Movement

	private void UpdateMovement()
	{
		if ( !Agent.IsValid() )
			return;

		CheckStuck();

		if ( WaitForDoor() || WaitForPlayer() )
			return;

		// Out of the heat before anything else, shooting on the way.
		if ( AvoidFire() )
			return;

		// Battle royale: getting into the zone comes first, shooting on the way.
		if ( HeadForZone() )
			return;

		if ( _targetVisible && _target.IsValid() )
		{
			Engage();
			return;
		}

		IsCrouching = false;

		if ( _target.IsValid() )
			Search();
		else if ( _contact.HasValue && _timeSinceContact < 12f && !_contactUnreachable )
			Investigate();
		else if ( IsObjectiveMode )
			Patrol();
		else
			Hunt( ApproachSpeed( _huntDestination ) );
	}

	/// <summary>
	/// On its way somewhere with no enemy in view, a bot sprints, gun carried, as a player does, and walks with it up only
	/// near where it's going: the last 700 units for the most cautious, 150 for the most aggressive. Where it's going is
	/// often only a guess (<see cref="HuntSpot"/>, a noise), so a bot can come round a corner at a run and have to stop and
	/// get its gun up (<see cref="SprintOutTime"/>). Bots used to move at 195-230 everywhere, gun carried but free to fire.
	/// </summary>
	private float ApproachSpeed( Vector3? destination )
	{
		var caution = MathX.Lerp( 700f, 150f, Aggression );
		return destination is { } point && WorldPosition.DistanceSquared( point ) < caution * caution ? _walkSpeed : _sprintSpeed;
	}

	/// <summary>
	/// Getting somewhere it must (out of the heat, into the zone): at a sprint, or at a walk with the gun up while an enemy
	/// is in view, so it can shoot on the way.
	/// </summary>
	private float UrgentSpeed => _targetVisible ? _walkSpeed : _sprintSpeed;

	private void Engage()
	{
		// Until they've registered the enemy, carry on with whatever they were doing, though a runner lets the sprint go
		// almost at once (SprintBreak).
		if ( _reactionEnds.Relative > 0f )
		{
			if ( _timeSinceAcquired > SprintBreak && Agent.MaxSpeed > _walkSpeed )
				Agent.MaxSpeed = _walkSpeed;
			return;
		}

		var toTarget = (_target.WorldPosition - WorldPosition).WithZ( 0f );
		var distance = toTarget.Length;
		var wanted = FightRange;

		// Too far for its liking: walk in, firing. Once it's fighting from about here it takes more to move it in again,
		// or it would switch every other frame at the edge.
		var closeInAt = wanted * Habits.CloseIn * (_move == Move.None ? 1f : 1.3f);
		if ( distance > closeInAt && !IsReloading && CloseIn( wanted ) )
			return;

		Manoeuvre( toTarget, distance, wanted );
	}

	/// <summary>
	/// Walk in on the enemy with the gun up, to a spot at its fighting range (<see cref="EngageSpot"/>), so it shoots on
	/// the way. A bot away from the players isn't worth going after: it keeps heading for the fight, shooting on the way.
	/// False if there's no walking there (up on a roof, into the gas): then it fights from where it is.
	/// </summary>
	private bool CloseIn( float wanted )
	{
		var speed = _walkSpeed * MathX.Lerp( 0.75f, 1f, Aggression );
		bool going;
		if ( _target is LightweightCombatBot && AwayFromAction( _target.WorldPosition ) && !IsObjectiveMode )
		{
			Hunt( speed );
			going = true;
		}
		else if ( OutsideZone( _target.WorldPosition ) )
			going = false;
		else
		{
			var spot = EngageSpot( wanted );
			going = GoTo( spot, speed );
			if ( going )
				_anchor = spot;
		}

		// Picked afresh once it's in range. Not when it can't get closer: the move it's on carries on.
		if ( going )
		{
			IsCrouching = false;
			_move = Move.None;
			_moveEnds = 0f;
		}

		return going;
	}

	/// <summary>
	/// Where to close in on the target to: a spot of the bot's own at about <paramref name="wanted"/> from them, on its
	/// side of them and clear of its teammates (<see cref="PickFreeSpot"/>). Every bot on one target used to walk onto
	/// the target's own position, so a team closing in ended up in a knot on top of them. Kept until the target has
	/// moved 250 units from where it was picked. A flanker's is off round their side, so it closes in on a curve.
	/// </summary>
	private Vector3 EngageSpot( float wanted )
	{
		var target = _target.WorldPosition;
		if ( _engageSpot.HasValue && _engageSpotFor.DistanceSquared( target ) < 250f * 250f )
			return _engageSpot.Value;

		_engageSpotFor = target;
		var fromTarget = (WorldPosition - target).WithZ( 0f );
		if ( Habits.Style == BotStyle.Flanker && _flankSign != 0f )
			fromTarget = Rotation.FromYaw( _flankSign * Game.Random.Float( 50f, 90f ) ) * fromTarget;
		var straight = target + (fromTarget.IsNearZeroLength ? Vector3.Zero : fromTarget.Normal * wanted * 0.8f);
		_engageSpot = PickFreeSpot( PointsToward( target, fromTarget, wanted * 0.6f, wanted ).Prepend( straight ) ) ?? target;
		return _engageSpot.Value;
	}

	/// <summary>
	/// Which way along <paramref name="side"/> the nearest teammate within <paramref name="range"/> is: 1, -1, or 0 with
	/// none that close.
	/// </summary>
	private float NearestTeammateSide( Vector3 side, float range )
	{
		if ( !HasTeammates )
			return 0f;

		var nearest = range * range;
		var result = 0f;
		foreach ( var mate in LivingBots )
		{
			if ( mate == this || mate.Team != Team )
				continue;

			var offset = (mate.WorldPosition - WorldPosition).WithZ( 0f );
			if ( offset.LengthSquared >= nearest )
				continue;

			nearest = offset.LengthSquared;
			result = offset.Dot( side ) >= 0f ? 1f : -1f;
		}

		return result;
	}

	/// <summary>
	/// Lost sight of the enemy: cover where they went for a moment, since most come back out where they went in, then go
	/// after them at a walk, gun up. How long it waits is its own (<see cref="BotHabits.Patience"/>): a rusher hardly at
	/// all, an anchor a few seconds. Past the first moment it shifts about its spot a little, as a player does holding an
	/// angle, rather than standing frozen; a marksman stays on the angle. An anchor or marksman only goes half way.
	/// </summary>
	private void Search()
	{
		var habits = Habits;
		if ( _timeSinceTargetSeen < habits.Patience )
		{
			// It finishes the move it was on: a new spot out of their sight, say, to come back out from.
			if ( _moveEnds.Relative > 0f && _move is Move.Push or Move.BackOff or Move.Relocate )
				return;

			if ( _timeSinceTargetSeen < 0.8f || habits.Style == BotStyle.Marksman )
				HoldPosition();
			else if ( _moveEnds.Relative <= 0f || _move is not (Move.Strafe or Move.Plant) )
			{
				var from = (WorldPosition - _lastSeenPosition).WithZ( 0f );
				if ( Game.Random.Float() < 0.35f )
					Plant( from.Length );
				else
					Strafe( from.IsNearZeroLength ? -WorldRotation.Forward : from.Normal, 0.6f );
			}

			return;
		}

		// Not worth hunting down a bot away from the players, or anyone into the zone's gas: back to the fight.
		if ( (_target is LightweightCombatBot && AwayFromAction( _lastSeenPosition )) || OutsideZone( _lastSeenPosition ) )
		{
			ForgetTarget();
			return;
		}

		// Where they were heading, or a spot of its own near there if a teammate's already on it.
		if ( !_searchPoint.HasValue )
		{
			var lead = NavPoint( _lastSeenPosition + _lastSeenVelocity.WithZ( 0f ) * 0.75f );
			if ( habits.Style is BotStyle.Anchor or BotStyle.Marksman )
				lead = NavPoint( Vector3.Lerp( WorldPosition, lead, 0.5f ) );
			_searchPoint = PickFreeSpot( PointsAround( lead, 0f, SpotSpread ).Prepend( lead ) ) ?? lead;
		}

		// A walk, not a run: they know someone's there. At the old 0.9 of MoveSpeed (207) the keenest ran after them,
		// gun down, and couldn't shoot when they came face to face.
		IsCrouching = false;
		if ( !GoTo( _searchPoint.Value, _walkSpeed * MathX.Lerp( 0.7f, 1f, Aggression ) ) )
		{
			ForgetTarget();
			return;
		}

		// Not there any more: carry on hunting from here.
		if ( WorldPosition.DistanceSquared( _searchPoint.Value ) < 96f * 96f )
			ForgetTarget();
	}

	/// <summary>
	/// Go and look where a noise or a callout came from. Cautious bots turn toward it and wait first, and walk more of the
	/// way in (<see cref="ApproachSpeed"/>), watching the threat. A callout reaches the whole team, so each bot goes for
	/// its own spot by it (<see cref="PickFreeSpot"/>) and the team closes in from several sides instead of piling onto
	/// one point.
	/// </summary>
	private void Investigate()
	{
		if ( _timeSinceContactStarted < MathX.Lerp( 2.5f, 0f, Aggression ) )
		{
			HoldPosition();
			return;
		}

		if ( OutsideZone( _contact.Value ) )
		{
			_contactUnreachable = true;
			return;
		}

		_contactSpot ??= PickFreeSpot( PointsAround( _contact.Value, 0f, SpotSpread ).Prepend( _contact.Value ) ) ?? _contact.Value;
		if ( !GoTo( _contactSpot.Value, ApproachSpeed( _contactSpot ) ) )
		{
			// Up on a roof, say: keep an eye on it, but carry on.
			_contactUnreachable = true;
			return;
		}

		if ( WorldPosition.DistanceSquared( _contactSpot.Value ) < 160f * 160f )
			_contact = null;
	}

	/// <summary>
	/// Head for where an enemy might be. Every few seconds on the way, the bot stays after the same enemy
	/// (<see cref="PickHuntTarget"/>) and its spot follows them (<see cref="HuntSpot"/>), or it carries on roaming to
	/// the same place. It used to guess afresh each time, often at another enemy or the far side of this one, and each
	/// new guess was a turn in the middle of a run. A new guess comes when it gets there.
	/// </summary>
	private void Hunt( float speed )
	{
		// An anchor or marksman holds each spot it gets to for a few seconds, watching, before moving up again.
		if ( _huntHold.Relative > 0f )
		{
			HoldPosition();
			return;
		}

		var arrived = _huntDestination.HasValue && WorldPosition.DistanceSquared( _huntDestination.Value ) < 128f * 128f;
		if ( arrived && !_huntHeld && Habits.HoldAtSpot > 0f )
		{
			_huntHeld = true;
			_huntHold = Habits.HoldAtSpot * Game.Random.Float( 0.5f, 1.3f );
			HoldPosition();
			return;
		}

		if ( !_huntDestination.HasValue || arrived || _nextHuntPick.Relative <= 0f )
		{
			_huntDestination = PickHuntDestination( arrived ? null : _huntDestination );
			_nextHuntPick = Game.Random.Float( 5f, 9f );
			_huntHeld = false;
		}

		if ( !GoTo( _huntDestination.Value, speed ) )
			_huntDestination = null;
	}

	/// <summary>
	/// Somewhere near an enemy, as if the team had a rough idea where they are, and the guess tightens as the bot closes
	/// in. Each bot takes its own spot (<see cref="PickFreeSpot"/>). Somewhere the bot can't walk to (Innocent Hotel's
	/// traitor room, roof and basement) is skipped, or it would stand at the nearest wall. <paramref name="current"/> is
	/// where the bot is still on its way to, if it is (see <see cref="Hunt"/>).
	/// </summary>
	private Vector3 PickHuntDestination( Vector3? current = null )
	{
		if ( GameUtils.IsBattleRoyale )
			return RoyaleHuntDestination( current );

		var enemies = new List<Component>();
		CollectEnemies( enemies );
		enemies.RemoveAll( x => !IsRealPlayer( x ) && AwayFromAction( x.WorldPosition ) );
		while ( enemies.Count > 0 )
		{
			var chosen = PickHuntTarget( enemies );
			enemies.Remove( chosen );

			if ( HuntSpot( chosen, current ) is { } destination )
				return destination;
		}

		return KeepRoaming( current ) ?? RegroupPoint() ?? RandomPatrolPoint();
	}

	/// <summary>
	/// Where to look for <paramref name="enemy"/>: somewhere around them, up to as far out as a guess from here could be,
	/// and never closer than 500 units (~13 m): without a sighting or a noise nobody knows which room someone is in. Down to
	/// 200 it brought bots to the player's corner already watching it.
	/// Still on the way to a guess at them (<paramref name="current"/>), it's the same guess, moved with them and pulled
	/// in toward them as it tightens, so the route bends with them instead of turning for a new one. Null if there's
	/// nowhere around them the bot can walk to.
	/// The guesses of bots after the same enemy are kept half the guess's size apart, and at least a third of it out from
	/// them, so a team hunting one player comes at them spread out over several sides rather than all to one spot.
	/// </summary>
	private Vector3? HuntSpot( Component enemy, Vector3? current )
	{
		var uncertainty = (enemy.WorldPosition.Distance( WorldPosition ) * 0.35f).Clamp( 500f, 1200f );
		if ( current.HasValue && enemy == _huntTarget )
		{
			var followed = NavPoint( enemy.WorldPosition + _huntGuess * MathF.Min( 1f, uncertainty / _huntUncertainty ) );
			if ( CanWalkTo( followed ) )
				return followed;
		}

		// A flanker's guess is off to one side of them, so it comes round rather than straight at them.
		var fromEnemy = (WorldPosition - enemy.WorldPosition).WithZ( 0f );
		var flank = Habits.Style == BotStyle.Flanker && !fromEnemy.IsNearZeroLength;
		if ( flank )
			_flankSign = Game.Random.Float() < 0.5f ? -1f : 1f;
		var around = flank
			? PointsToward( enemy.WorldPosition, Vector3.Cross( fromEnemy.Normal, Vector3.Up ) * _flankSign, uncertainty * 0.35f, uncertainty )
			: PointsAround( enemy.WorldPosition, uncertainty * 0.35f, uncertainty );
		if ( PickFreeSpot( around, uncertainty * 0.5f ) is not { } spot )
			return null;

		_huntTarget = enemy;
		_huntGuess = (spot - enemy.WorldPosition).WithZ( 0f );
		_huntUncertainty = uncertainty;
		return spot;
	}

	/// <summary>
	/// Nobody to go after. Still on the way to somewhere that wasn't a guess at an enemy (<paramref name="current"/>),
	/// carry on there rather than turn for somewhere new. Null otherwise.
	/// </summary>
	private Vector3? KeepRoaming( Vector3? current )
	{
		var roaming = _huntTarget is null;
		_huntTarget = null;
		if ( roaming && current is { } point && !OutsideZone( point ) )
			return point;

		return null;
	}

	/// <summary> No enemy near the players to go after (the player's own teammates, say): move up with the players. </summary>
	private Vector3? RegroupPoint()
	{
		PlayerPawn player = null;
		foreach ( var pawn in LivingPlayers )
		{
			if ( !player.IsValid() || pawn.WorldPosition.DistanceSquared( WorldPosition ) < player.WorldPosition.DistanceSquared( WorldPosition ) )
				player = pawn;
		}

		if ( !player.IsValid() )
			return null;

		return PickFreeSpot( PointsAround( player.WorldPosition, 300f, 800f ) );
	}

	/// <summary>
	/// Which of <paramref name="spots"/> to go for: the first, unless a teammate is standing on it or headed there, then
	/// the first of the rest that's clear of them, or failing that the least crowded. Bots going after the same enemy,
	/// noise or callout each take their own spot and close in from several sides, instead of all walking the same
	/// corridor to the same point. Null if the first can't be walked to (up on a roof, say), whatever the rest are.
	/// Clear means <paramref name="spacing"/> from everyone else's (<see cref="Interval"/> unless given).
	/// </summary>
	private Vector3? PickFreeSpot( IEnumerable<Vector3> spots, float spacing = Interval )
	{
		var taken = SpotScratch;
		taken.Clear();
		AddTeamSpots( taken );
		Vector3? best = null;
		var bestClearance = -1f;
		foreach ( var spot in spots )
		{
			var point = NavPoint( spot );
			if ( !CanWalkTo( point ) )
			{
				// Only the first spot gets here with none in hand: the place itself, or the bot's guess at it, is out of reach.
				if ( !best.HasValue )
					return null;

				continue;
			}

			var clearance = float.MaxValue;
			foreach ( var other in taken )
				clearance = MathF.Min( clearance, other.Distance( point ) );
			if ( clearance >= spacing )
				return point;

			if ( clearance > bestClearance )
			{
				best = point;
				bestClearance = clearance;
			}
		}

		return best;
	}

	/// <summary> <see cref="SpotTries"/> random points <paramref name="minRadius"/> to <paramref name="maxRadius"/> out from <paramref name="centre"/>. </summary>
	private static IEnumerable<Vector3> PointsAround( Vector3 centre, float minRadius, float maxRadius )
	{
		for ( var i = 0; i < SpotTries; i++ )
		{
			var direction = Vector3.Random.WithZ( 0f );
			if ( direction.IsNearZeroLength )
				direction = Vector3.Forward;

			yield return centre + direction.Normal * Game.Random.Float( minRadius, maxRadius );
		}
	}

	/// <summary>
	/// Like <see cref="PointsAround"/>, but only within 70 degrees either side of <paramref name="toward"/> from
	/// <paramref name="centre"/>: somewhere on this side of them, not past them.
	/// </summary>
	private static IEnumerable<Vector3> PointsToward( Vector3 centre, Vector3 toward, float minRadius, float maxRadius )
	{
		var heading = toward.IsNearZeroLength ? 0f : MathF.Atan2( toward.y, toward.x ).RadianToDegree();
		for ( var i = 0; i < SpotTries; i++ )
		{
			var angle = (heading + Game.Random.Float( -70f, 70f )).DegreeToRadian();
			yield return centre + new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f ) * Game.Random.Float( minRadius, maxRadius );
		}
	}

	/// <summary> Adds where this bot's teammates are, and where the bots among them are headed, to <paramref name="spots"/>. </summary>
	private void AddTeamSpots( List<Vector3> spots )
	{
		if ( !HasTeammates )
			return;

		foreach ( var mate in LivingBots )
		{
			if ( mate == this || mate.Team != Team )
				continue;

			spots.Add( mate.WorldPosition );
			if ( mate._moveTarget is { } target )
				spots.Add( target );
		}

		foreach ( var player in LivingPawns )
		{
			if ( player.Team == Team )
				spots.Add( player.WorldPosition );
		}
	}

	/// <summary> Does this bot have a side? Not in free-for-all. </summary>
	private bool HasTeammates => !GameUtils.IsFreeForAllMode && Team != Team.Unassigned;

	/// <summary>
	/// Is <paramref name="position"/> further than <see cref="ActionRadius"/> from every living real player? Never in
	/// battle royale, where bots fight wherever they meet, so the field thins out.
	/// While every real player is down and about to respawn (<see cref="BotSystem.AwaitingRespawn"/>) it's everywhere:
	/// the bots don't start fights of their own meanwhile (they still shoot anyone who comes at them). They used to go
	/// at each other all over the map, and the player came back to a knot of bots fighting over there. With no respawn
	/// coming (a round mode), nobody's coming back, so they finish the round.
	/// </summary>
	private bool AwayFromAction( Vector3 position )
	{
		if ( GameUtils.IsBattleRoyale )
			return false;

		var players = LivingPlayers;
		foreach ( var player in players )
		{
			if ( player.WorldPosition.DistanceSquared( position ) < ActionRadius * ActionRadius )
				return false;
		}

		return players.Count > 0 || (BotSystem.Current?.AwaitingRespawn ?? false);
	}

	/// <summary>
	/// Real players are the objective: while there's one on the other side, bots go for them (the nearest most likely)
	/// and only fight other bots they run into on the way. Otherwise they go for the enemy bots nearest the players,
	/// where the fight is, rather than starting their own somewhere out of sight. A bot stays after the one it picked for
	/// 20 to 30 s while they're still one to go after, so it doesn't swap back and forth between two.
	/// </summary>
	private Component PickHuntTarget( List<Component> enemies )
	{
		var players = enemies.Where( IsRealPlayer ).ToList();
		var candidates = players.Count > 0 ? players : enemies;
		if ( _nextHuntTargetPick.Relative > 0f && candidates.Contains( _huntTarget ) )
			return _huntTarget;

		_nextHuntTargetPick = Game.Random.Float( 20f, 30f );
		var action = LivingPlayers.Select( x => x.WorldPosition ).ToList();

		var chosen = candidates[0];
		var total = 0f;
		foreach ( var enemy in candidates )
		{
			var weight = 1f / (enemy.WorldPosition.Distance( WorldPosition ) + 600f);
			if ( enemy is LightweightCombatBot && action.Count > 0 )
				weight /= action.Min( x => x.Distance( enemy.WorldPosition ) ) + 600f;

			total += weight;
			if ( Game.Random.Float( 0f, total ) < weight )
				chosen = enemy;
		}

		return chosen;
	}

	private void Patrol()
	{
		if ( !_patrolTarget.HasValue || _timeSincePatrolPick > 10f || WorldPosition.DistanceSquared( _patrolTarget.Value ) < 96f * 96f )
		{
			_timeSincePatrolPick = 0f;
			_patrolTarget = FindPatrolTarget();
		}

		GoTo( _patrolTarget.Value, ApproachSpeed( _patrolTarget ) );
	}

	private Vector3 FindPatrolTarget()
	{
		// Hot Zone game mode integration: capture the active zone
		var activeHardpoints = Scene.GetAllComponents<HardpointZone>().ToList();
		if ( activeHardpoints.Count > 0 )
		{
			var targetZone = Game.Random.FromList( activeHardpoints );
			return ObjectiveSpot( targetZone.WorldPosition );
		}

		// Domination game mode integration: capture active flags
		var activeFlags = Scene.GetAllComponents<DominationFlag>().ToList();
		if ( activeFlags.Count > 0 )
		{
			// Go to a random uncapped/enemy flag to capture it, or defend one once they're all ours.
			var enemyFlags = activeFlags.Where( x => x.ControllingTeam != Team ).ToList();
			var targetFlag = Game.Random.FromList( enemyFlags.Count > 0 ? enemyFlags : activeFlags );
			return ObjectiveSpot( targetFlag.WorldPosition );
		}

		return RandomPatrolPoint();
	}

	/// <summary>
	/// A spot of the bot's own inside a capture zone (radius 300), clear of its teammates (<see cref="PickFreeSpot"/>).
	/// Every bot used to go to within 90 units of the zone's middle, a knot a single burst could take out.
	/// </summary>
	private Vector3 ObjectiveSpot( Vector3 zone ) =>
		PickFreeSpot( PointsAround( zone, 40f, 240f ) )
		?? NavPoint( zone + Vector3.Random.WithZ( 0f ).Normal * Game.Random.Float( 30f, 90f ) );

	private Vector3 RandomPatrolPoint()
	{
		var point = WorldPosition;
		for ( var i = 0; i < 4; i++ )
		{
			var direction = Vector3.Random.WithZ( 0f );
			if ( direction.LengthSquared < 0.01f )
				direction = WorldRotation.Forward;

			point = NavPoint( WorldPosition + direction.Normal * Game.Random.Float( PatrolRadius * 0.35f, PatrolRadius ) );
			if ( CanWalkTo( point ) )
				break;
		}

		return point;
	}

	/// <summary>
	/// Walk there, if the navmesh joins up with it. Roofs and sealed rooms are islands: walking at one only parks the bot
	/// at the nearest point, under or beside it, where the others pile up too. So for one of those the bot stays put and
	/// this is false.
	/// </summary>
	/// <remarks> A few metres' step in a fight skips the route check (<paramref name="checkPath"/> false). </remarks>
	private bool GoTo( Vector3 position, float speed, bool checkPath = true )
	{
		// Hardcore: a shot leg or foot. And never on the heels of a teammate.
		Agent.MaxSpeed = KeepInterval( speed ) * (HealthComponent.IsValid() ? HealthComponent.WoundSpeedScale : 1f);
		// Each new destination is a navmesh search or two. The route to a far one hardly changes as it moves a little,
		// so re-route when it has moved a twenty-fifth of the way from here.
		var tolerance = BotSystem.LodEnabled ? MathF.Max( 48f, WorldPosition.Distance( position ) * 0.04f ) : 48f;
		if ( _moveTarget.HasValue && _moveTarget.Value.DistanceSquared( position ) < tolerance * tolerance )
			return true;
		if ( _unreachable.HasValue && _timeSinceUnreachable < 2f && _unreachable.Value.DistanceSquared( position ) < 48f * 48f )
			return false;

		var point = NavPoint( position );
		if ( checkPath && !CanWalkTo( point ) )
		{
			_unreachable = position;
			_timeSinceUnreachable = 0f;
			HoldPosition();
			return false;
		}

		_moveTarget = position;
		Agent.MoveTo( point );
		return true;
	}

	/// <summary> Where the bot is getting out of the heat to, and when it next feels how hot it is. </summary>
	private Vector3? _fireEscape;
	private TimeUntil _nextHeatCheck;

	/// <summary>
	/// A person steps out of heat that hurts (past <see cref="SurfaceFire.HarmlessFlux"/>), to the nearest spot where it
	/// doesn't: often ground the fire has already burnt. It keeps going until it gets there or the heat is well down.
	/// Heat isn't shaded by walls here, so bots are a little more careful than they need to be.
	/// </summary>
	private bool AvoidFire()
	{
		if ( _nextHeatCheck <= 0f )
		{
			_nextHeatCheck = 0.5f;
			var heat = SurfaceFire.HeatAt( Scene, WorldPosition, out var from );
			var arrived = _fireEscape.HasValue
				&& _fireEscape.Value.WithZ( 0 ).DistanceSquared( WorldPosition.WithZ( 0 ) ) < 48f * 48f;

			if ( heat <= SurfaceFire.HarmlessFlux * (_fireEscape.HasValue && !arrived ? 0.5f : 1f) )
				_fireEscape = null;
			else if ( !_fireEscape.HasValue || arrived
			          || SurfaceFire.HeatAt( Scene, _fireEscape.Value, out _ ) > SurfaceFire.HarmlessFlux )
				_fireEscape = FindFireEscape( from );
		}

		if ( _fireEscape is not { } escape )
			return false;

		IsCrouching = false;
		if ( GoTo( escape, UrgentSpeed ) )
			return true;

		_fireEscape = null;
		return false;
	}

	/// <summary>
	/// The nearest bearable spot 150 to 450 units off, trying straight away from the heat first, then further round;
	/// failing that, the coolest one.
	/// </summary>
	private Vector3? FindFireEscape( Vector3 from )
	{
		var away = (WorldPosition - from).WithZ( 0 );
		var baseAngle = away.IsNearZeroLength ? Game.Random.Float( 0f, MathF.PI * 2f ) : MathF.Atan2( away.y, away.x );
		Vector3? coolest = null;
		var coolestHeat = float.MaxValue;

		for ( var distance = 150f; distance <= 450f; distance += 150f )
		{
			for ( var k = 0; k < 8; k++ )
			{
				// 0, then 40 degrees either way, 80, 120, and straight back last.
				var turn = k == 7 ? MathF.PI : ((k + 1) / 2) * 0.7f * (k % 2 == 1 ? 1f : -1f);
				var angle = baseAngle + turn;
				var candidate = NavPoint( WorldPosition + new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f ) * distance );
				var heat = SurfaceFire.HeatAt( Scene, candidate, out _ );
				if ( heat <= SurfaceFire.HarmlessFlux * 0.5f )
					return candidate;

				if ( heat < coolestHeat )
				{
					coolestHeat = heat;
					coolest = candidate;
				}
			}
		}

		return coolest;
	}

	private void HoldPosition()
	{
		if ( !_moveTarget.HasValue )
			return;

		_moveTarget = null;
		Agent?.Stop();
	}

	/// <summary>
	/// The navmesh point nearest <paramref name="position"/>. Every place a bot heads for comes through here, so in a
	/// Skirmish held to an arena it's kept inside it (<see cref="SkirmishArena.Clamp"/>).
	/// </summary>
	private Vector3 NavPoint( Vector3 position )
	{
		position = SkirmishArena.Clamp( position );
		return Scene.NavMesh.GetClosestPoint( position ) ?? position;
	}

	/// <summary> Maps have navmesh islands nobody can walk to, like a sealed traitor room behind a wall. </summary>
	private bool CanWalkTo( Vector3 position ) => Scene.NavMesh.CalculatePath( new Sandbox.Navigation.CalculatePathRequest
	{
		Start = WorldPosition,
		Target = position
	} ).Status == Sandbox.Navigation.NavMeshPathStatus.Complete;

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

	/// <summary>
	/// A player in the way. The navmesh doesn't know about players, so a bot would walk into one, and its movement box
	/// (<see cref="AttachMovementBox"/>) would shove them about. Wait a moment instead, like a person.
	/// </summary>
	private bool WaitForPlayer()
	{
		if ( _playerInTheWay.Relative > 0f )
			return true;

		var velocity = Agent.Velocity.WithZ( 0f );
		if ( velocity.Length < 10f )
			return false;

		var ahead = velocity.Normal;
		foreach ( var player in LivingPawns )
		{
			var offset = player.WorldPosition - WorldPosition;
			if ( MathF.Abs( offset.z ) > 64f )
				continue;

			// Both boxes are 32 wide: stop a step short of theirs, for anyone the next stride would clip.
			var along = Vector3.Dot( offset.WithZ( 0f ), ahead );
			if ( along < 0f || along > 56f || (offset.WithZ( 0f ) - ahead * along).Length > 36f )
				continue;

			_playerInTheWay = 0.5f;
			_moveTarget = null;
			Agent.Stop();
			return true;
		}

		return false;
	}

	/// <summary>
	/// Soldiers on the move keep an interval. Coming up behind a teammate who's going the same way, the bot eases off
	/// until the gap opens again, so a team heading down one corridor strings out into a spaced file instead of walking
	/// in a bunch. A teammate standing still or coming the other way is just passed.
	/// </summary>
	private float KeepInterval( float speed )
	{
		var velocity = Agent.Velocity.WithZ( 0f );
		if ( velocity.Length < 10f )
			return speed;

		var ahead = velocity.Normal;
		var scale = 1f;
		if ( HasTeammates )
		{
			foreach ( var mate in LivingBots )
			{
				if ( mate != this && mate.Team == Team )
					scale = MathF.Min( scale, IntervalScale( mate, ahead ) );
			}

			foreach ( var player in LivingPawns )
			{
				if ( player.Team == Team )
					scale = MathF.Min( scale, IntervalScale( player, ahead ) );
			}
		}

		return speed * MathF.Max( scale, 0.25f );
	}

	/// <summary> How much to ease off for a teammate going our way just in front (1 for anyone else). </summary>
	private float IntervalScale( Component mate, Vector3 ahead )
	{
		var offset = mate.WorldPosition - WorldPosition;
		if ( MathF.Abs( offset.z ) > 64f || GetVelocity( mate ).WithZ( 0f ).Dot( ahead ) < 40f )
			return 1f;

		var along = Vector3.Dot( offset.WithZ( 0f ), ahead );
		if ( along <= 0f || along >= Interval || (offset.WithZ( 0f ) - ahead * along).Length > 64f )
			return 1f;

		return along / Interval;
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
		// Not at a sprint, or for a moment after while the gun comes up, as for a player (SprintOutTime).
		if ( IsReloading || !_targetVisible || !IsEnemyAlive( _target )
			|| _reactionEnds.Relative > 0f || _nextShot.Relative > 0f || _timeSinceSprinting < SprintOutTime )
			return;

		var toPoint = LiveTargetPoint - EyePosition;
		var distance = toPoint.Length;
		// Still swinging onto them.
		if ( distance > EngageRange || Vector3.GetAngle( _aimDirection, toPoint ) > 8f )
			return;

		if ( _burstRemaining <= 0 )
		{
			(_burstRemaining, _splitTime) = RollString( distance );
			_stringsHere++;
		}

		FireShot( toPoint.Normal );
		_burstRemaining--;
		_nextShot = _burstRemaining > 0 ? _splitTime : PauseAfter( distance );
	}

	/// <summary> Up to here is close quarters (~15 m), where soldiers fire short bursts. </summary>
	private const float CloseQuarters = 600f;
	/// <summary> Up to here (~40 m), controlled pairs; past it, aimed single shots. </summary>
	private const float ControlledPairRange = 1600f;
	private const float UnitsPerMetre = 39.37f;

	/// <summary>
	/// The next string of fire: how many rounds, and how far apart. Soldiers are trained to fire aimed shots, not to hose
	/// (FM 3-22.9): at range a single round at a time, each aimed; closer in, a controlled pair (two quick aimed presses);
	/// and automatic only up close, in short bursts, where hitting first matters more than the rounds. The fire team's
	/// automatic rifleman (an LMG) fires short bursts at every range. Bots used to fire 3-7 round bursts under 13 m and 2-4
	/// under 33 m, a quarter to half a second apart: five to eight rounds a second at anyone in view.
	/// </summary>
	private (int Rounds, float Split) RollString( float distance )
	{
		// A second aimed press of the trigger, as in a controlled pair: 0.2 s for a veteran, 0.32 s for a recruit.
		var press = _hasSemi ? MathF.Max( MathX.Lerp( 0.32f, 0.2f, Skill ), _cycleTime ) : _cycleTime;
		// A burst-only gun (neither semi nor automatic) fires what one pull gives it.
		if ( !_hasSemi && !_hasAutomatic && _burstLength > 0 )
			return (_burstLength, _cycleTime);

		if ( _isMachineGunner && _hasAutomatic )
			return (Game.Random.Int( 3, distance < CloseQuarters ? 6 : 5 ), _cycleTime);

		if ( distance < CloseQuarters )
		{
			if ( _hasAutomatic )
				return (Game.Random.Int( 2, _isSubmachineGun ? 5 : 4 ), _cycleTime);
			if ( _burstLength > 1 )
				return (_burstLength, _cycleTime);
			return (2, press);
		}

		// A marksman fires single aimed rounds outside close quarters.
		if ( distance < ControlledPairRange && Habits.Style != BotStyle.Marksman )
			return (Game.Random.Float() < 0.6f ? 2 : 1, press);

		return (1, press);
	}

	/// <summary>
	/// The pause after a string: riding the recoil, finding the target again and aiming, the longer the further off they
	/// are. Rapid aimed fire is about 45 rounds a minute, one every 1.3 s, for a trained rifleman at 100 m and beyond
	/// (FM 3-22.9). Up close a good shot is back on target in a quarter to half a second. A machine gunner's rapid rate is
	/// a burst every 2-4 s at range, less up close.
	/// </summary>
	private float PauseAfter( float distance )
	{
		var metres = distance / UnitsPerMetre;
		float pause;
		if ( _isMachineGunner && _hasAutomatic )
			pause = distance < CloseQuarters ? MathX.Lerp( 0.9f, 0.5f, Skill ) : MathX.Lerp( 2.4f, 1.4f, Skill ) + metres * 0.004f;
		else if ( distance < CloseQuarters )
			pause = MathX.Lerp( 0.55f, 0.3f, Skill );
		else if ( distance < ControlledPairRange )
			pause = MathX.Lerp( 0.9f, 0.5f, Skill );
		else
			pause = MathX.Lerp( 1.4f, 0.8f, Skill ) + metres * 0.004f;

		// A marksman takes longer over each shot; a rusher is quicker back on them.
		pause *= Habits.Style switch { BotStyle.Marksman => 1.15f, BotStyle.Rusher => 0.9f, _ => 1f };
		return pause * Game.Random.Float( 0.8f, 1.3f );
	}

	private void FireShot( Vector3 direction )
	{
		// A random point in the error cone, with recoil walking the muzzle up.
		var error = AimError();
		var angle = Game.Random.Float( 0f, MathF.PI * 2f );
		var radius = error * MathF.Sqrt( Game.Random.Float() );
		var spread = Rotation.From( radius * MathF.Sin( angle ) - _recoil * 0.4f, radius * MathF.Cos( angle ), 0f );
		var shotDirection = (Rotation.LookAt( direction ) * spread).Forward;

		// Rounds go through window glass, breaking it.
		var trace = Scene.Trace.Ray( EyePosition, EyePosition + shotDirection * (EngageRange + 1000f) )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "playerclip", "movement", BreakableGlass.Tag )
			.UseHitboxes()
			.Run();
		BreakableGlass.BreakAlong( Scene, EyePosition, trace.EndPosition );

		_magazine--;
		_recoil += RecoilPerShot;
		TimeSinceFired = 0f;
		// Send the firing weapon's ammo choice with the shot so every observer sees the same effect.
		DoShootEffects( GetMuzzlePosition(), trace.EndPosition, UsesTracerRounds, trace.Hit );

		if ( trace.Hit )
			ApplyHit( trace, shotDirection );
	}

	/// <summary> Whoever hostile the round hits takes it, not only the enemy being aimed at. </summary>
	private void ApplyHit( SceneTraceResult trace, Vector3 direction )
	{
		var victim = HitTarget( trace.GameObject, _target ) ? _target : EnemyHitBy( trace.GameObject );
		if ( !IsEnemyAlive( victim ) )
			return;

		// A round through an arm held across the body goes on into it.
		var hitbox = trace.ThroughBody( Scene ).GetHitboxTags();
		if ( hitbox == HitboxTags.None )
			hitbox = HitboxTags.Chest;

		var roundDamage = RoundDamage( trace.Distance );
		var damage = victim is PlayerPawn ? roundDamage * RealPlayerDamageScale : roundDamage;
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

	/// <summary> The enemy <paramref name="hit"/> belongs to, if any. </summary>
	private Component EnemyHitBy( GameObject hit )
	{
		foreach ( var bot in LivingBots )
		{
			if ( bot != this && HitTarget( hit, bot ) && IsEnemyAlive( bot ) )
				return bot;
		}

		foreach ( var player in LivingPawns )
		{
			if ( HitTarget( hit, player ) && IsEnemyAlive( player ) )
				return player;
		}

		return null;
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
			// The gun's own reload (an RPK's drum takes far longer than an M4's mag), slower for green bots.
			var reloadTime = _magazine <= 0 ? _emptyReloadTime : _reloadTime;
			_reloadEnds = reloadTime * MathX.Lerp( 1.45f, 1.05f, Skill ) * Game.Random.Float( 0.9f, 1.1f );
			PlayReloadAnimation();
		}
	}

	[Rpc.Broadcast]
	private void PlayReloadAnimation()
	{
		_sinceReloadClip = 0f;
		Renderer?.SetBool( "b_reload", true );
	}

	#endregion
}
