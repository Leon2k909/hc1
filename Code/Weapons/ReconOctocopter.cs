using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A recon aircraft flown from a rugged tablet: the coaxial X8 or the hand-launched nano helicopter. Its prefab sets
/// its size, flight limits, rotors and camera. The operator stays in their body (it can be shot, and they
/// hear the world from it) and sees through the drone's camera on the tablet.
/// <para>
/// The owner (the operator's machine) flies it and syncs its transform. The host takes its damage and spots enemies
/// through its camera. Every machine spins its rotors and plays their sound.
/// </para>
/// <para>
/// The flight is position-hold, as a GPS drone's is: the sticks command a velocity relative to the camera's heading,
/// and the airframe tilts into the thrust that velocity needs (with drag), the way a multirotor accelerates.
/// </para>
/// </summary>
public sealed class ReconOctocopter : Component, Component.IDamageable, ICustomMinimapIcon,
	IGameEventHandler<ResetScoresEvent>, IGameEventHandler<BetweenRoundCleanupEvent>
{
	public enum FlightState
	{
		Spooling,
		TakingOff,
		Flying,
		Landing,
		Landed,
		Falling,
		Wreck
	}

	private const float Metre = 39.37f;
	private const float Gravity = 9.81f * Metre;

	/// <summary>On the drone while its own feed is up, which leaves it out of the picture.</summary>
	private const string OwnDroneTag = "own_drone";

	/// <summary>The gimbal's model: its origin is the pivot, and the lens is <see cref="LensOffset"/> along its +X.</summary>
	[Property] public GameObject Gimbal { get; set; }
	[Property] public SoundEvent RotorSound { get; set; }
	[Property] public PrefabFile SparksPrefab { get; set; }
	[Property] public string DisplayName { get; set; } = "Recon Octocopter";
	[Property] public string IconPath { get; set; } = "ui/weapons/recon_octocopter.svg";
	[Property] public string StationResourcePath { get; set; } = "weapons/recon_octocopter/recon_octocopter.equip";

	/// <summary>A short hand release before automatically opening the tablet's feed.</summary>
	[Property, Group( "Launch" )] public bool HandLaunched { get; set; }
	[Property, Group( "Launch" )] public float LinkDelay { get; set; }
	[Property, Group( "Launch" )] public float SpoolSeconds { get; set; } = 1.2f;

	/// <summary>Where the lens sits from the gimbal's pivot (inches, the gimbal model's space).</summary>
	[Property] public Vector3 LensOffset { get; set; } = new( 1.969f, 0f, 0f );

	/// <summary>The airframe's box for collisions, from the drone's origin: the rotor tips and the skids.</summary>
	[Property] public BBox Hull { get; set; } = new( new Vector3( -30f, -30f, -16.7f ), new Vector3( 30f, 30f, 7f ) );
	[Property] public bool RotateCollisionHull { get; set; }

	[Property, Group( "Flight" )] public float CruiseSpeed { get; set; } = 12f * Metre;
	[Property, Group( "Flight" )] public float SportSpeed { get; set; } = 18f * Metre;
	[Property, Group( "Flight" )] public float Acceleration { get; set; } = 7f * Metre;
	[Property, Group( "Flight" )] public float ClimbRate { get; set; } = 5f * Metre;
	[Property, Group( "Flight" )] public float DescentRate { get; set; } = 3f * Metre;
	[Property, Group( "Flight" )] public float VerticalAcceleration { get; set; } = 5f * Metre;

	/// <summary>Highest it climbs above where it took off.</summary>
	[Property, Group( "Flight" )] public float Ceiling { get; set; } = 120f * Metre;

	/// <summary>The hover it climbs to after taking off.</summary>
	[Property, Group( "Flight" )] public float TakeoffHeight { get; set; } = 2.5f * Metre;

	/// <summary>
	/// Seconds of flight from a full battery: a game limit set by each aircraft's prefab.
	/// </summary>
	[Property, Group( "Flight" )] public float BatterySeconds { get; set; } = 90f;

	/// <summary>Drag as acceleration per speed squared, per inch: ½ ρ Cd·A / m for ~0.13 m² and ~9 kg.</summary>
	[Property, Group( "Flight" )] public float DragPerInch { get; set; } = 0.000246f;

	[Property, Group( "Flight" )] public float MaxTilt { get; set; } = 35f;

	/// <summary>Rotor speed at hover. Two blades at that speed pass ~97 times a second.</summary>
	[Property, Group( "Flight" )] public float HoverRpm { get; set; } = 2900f;

	[Property, Group( "Damage" )] public float MaxIntegrity { get; set; } = 60f;

	/// <summary>Hitting something faster than this damages it.</summary>
	[Property, Group( "Damage" )] public float CrashSpeed { get; set; } = 200f;
	[Property, Group( "Damage" )] public float ImpactDamageThreshold { get; set; } = 150f;

	[Property, Group( "Camera" )] public float MaxGimbalPitch { get; set; } = 90f;
	[Property, Group( "Camera" )] public float MinGimbalPitch { get; set; } = -20f;

	/// <summary>The camera's widest horizontal field of view, at 1x.</summary>
	[Property, Group( "Camera" )] public float WideFieldOfView { get; set; } = 62f;

	/// <summary>
	/// How far it makes out a person at 1x: the Johnson criterion for recognising one (6 line pairs across their
	/// width) on a 1080p sensor at 62 degrees, ~92 m. Zoom multiplies it.
	/// </summary>
	[Property, Group( "Camera" )] public float SpotRange { get; set; } = 3600f;

	public static readonly float[] ZoomSteps = { 1f, 2f, 4f, 8f, 16f, 30f };
	[Property, Group( "Camera" )] public float[] CameraZoomSteps { get; set; } = ZoomSteps.ToArray();
	[Property, Group( "Camera" )] public float CameraNearPlane { get; set; } = 1f;

	[Sync] public PlayerPawn Operator { get; private set; }
	[Sync] public Team ReconTeam { get; private set; }
	[Sync] public bool IsLinked { get; private set; }
	[Sync] public FlightState State { get; private set; }

	/// <summary>Where the camera points: world yaw, and pitch with positive down (the s&amp;box convention).</summary>
	[Sync] public float CameraYaw { get; private set; }
	[Sync] public float GimbalPitch { get; private set; }
	[Sync] public float Zoom { get; private set; } = 1f;

	/// <summary>The rotors' thrust over the drone's weight.</summary>
	[Sync] public float Throttle { get; private set; }
	[Sync] public float Battery { get; private set; } = 1f;

	[Sync( SyncFlags.FromHost )] public float Integrity { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsDestroyed { get; private set; }
	[Sync( SyncFlags.FromHost )] private NetList<Guid> Contacts { get; set; } = new();

	/// <summary>The drone this machine is flying, if any.</summary>
	public static ReconOctocopter Piloted { get; private set; }

	private static TimeSince _sinceUnlinked = 10f;

	public static bool IsPiloting( PlayerPawn pawn ) => pawn.IsValid() && Piloted.IsValid() && Piloted.IsLinked
		&& Piloted.Operator == pawn;

	/// <summary>Just back from the drone: the key that brought you back shouldn't also use whatever's in front of you.</summary>
	public static bool JustUnlinked => _sinceUnlinked < 0.25f;

	/// <summary>The camera the drone's feed is drawn with, while it's piloted.</summary>
	public CameraComponent FeedCamera { get; private set; }

	public float AltitudeMetres => (WorldPosition.z - _launchZ) / Metre;
	public float SpeedMetres => _velocity.Length / Metre;
	public bool LowBattery => Battery < 0.15f;
	public bool IsAutoLanding => State == FlightState.Landing && _forcedLanding;
	public float HorizontalFieldOfView => FieldOfViewFor( Zoom, WideFieldOfView );
	public bool IsHandReleasing => HandLaunched && !IsProxy && _linkOnStart && _sinceLaunched < LinkDelay;
	public float HandReleaseProgress => Math.Clamp( (float)_sinceLaunched / MathF.Max( LinkDelay, 0.01f ), 0f, 1f );
	public float[] AvailableZoomSteps => CameraZoomSteps is { Length: > 0 } ? CameraZoomSteps : ZoomSteps;

	private Vector3 _velocity;
	private Vector3 _lastVelocity;
	private float _launchZ;
	private float _bodyYaw;
	private float _yawTarget;
	private float _pitchTarget;
	private float _stateTime;
	private bool _forcedLanding;
	private bool _linkOnStart;
	private TimeSince _sinceLaunched = 100f;
	private float _lastHealth;
	private TimeSince _sinceLinked;
	private Rotation _tumble = Rotation.Identity;
	private Vector3 _spin;
	private CameraComponent _bodyCamera;
	private GameObject _cameraObject;
	private SoundHandle _rotorSound;
	private ReconRotor[] _rotors;
	private float _rpm;
	private TimeSince _sinceScan;
	private readonly Dictionary<Guid, TimeSince> _lastSeen = new();
	private TimeSince _sinceImpact = 1f;

	public static float FieldOfViewFor( float zoom, float wideFieldOfView = 62f ) =>
		ReconFlightMath.FieldOfView( zoom, wideFieldOfView );

	public BBox CollisionHullFor( Rotation rotation ) => RotateCollisionHull
		? ReconFlightMath.RotatedHull( Hull, rotation ) : Hull;

	/// <summary>Set up on the operator's machine before it's network spawned.</summary>
	public void Initialize( PlayerPawn op )
	{
		Operator = op;
		ReconTeam = op.Team;
		CameraYaw = _yawTarget = _bodyYaw = op.EyeAngles.yaw;
		GimbalPitch = _pitchTarget = 10f;
		Zoom = 1f;
		Battery = 1f;
		State = FlightState.Spooling;
		_sinceLaunched = 0;
		_launchZ = WorldPosition.z;
		_linkOnStart = true;
		WorldRotation = Rotation.FromYaw( _bodyYaw );

		// One drone an operator: a new launch retires the last one.
		foreach ( var previous in Scene.GetAllComponents<ReconOctocopter>().Where( d => d != this && d.Operator == op ).ToArray() )
			if ( !previous.IsProxy ) previous.GameObject.Destroy();
	}

	protected override void OnStart()
	{
		_rotors = Components.GetAll<ReconRotor>( FindMode.EverythingInDescendants ).ToArray();
		if ( Networking.IsHost && Integrity <= 0f && !IsDestroyed )
			Integrity = MaxIntegrity;
		if ( !IsProxy )
		{
			Network.SetOrphanedMode( NetworkOrphaned.Destroy );
			if ( _launchZ == 0f ) _launchZ = WorldPosition.z;
			if ( _linkOnStart && LinkDelay <= 0f )
			{
				_linkOnStart = false;
				Link();
			}
		}
	}

	protected override void OnDestroy()
	{
		Unlink();
		_rotorSound?.Stop( 0.2f );
		_rotorSound = null;
	}

	protected override void OnDisabled()
	{
		Unlink();
	}

	// ---- The link --------------------------------------------------------------------------------------------------

	/// <summary>Look through the drone's camera and take the sticks. Only on the operator's machine.</summary>
	public void Link()
	{
		if ( IsProxy || IsLinked || IsDestroyed || !Operator.IsValid() || !Operator.IsLocallyControlled ) return;
		if ( Operator.HealthComponent.State != LifeState.Alive ) return;
		if ( Piloted.IsValid() && Piloted != this ) Piloted.Unlink();

		var station = Operator.Inventory.Equipment.FirstOrDefault( e => string.Equals(
			e.Resource?.ResourcePath, StationResourcePath, StringComparison.OrdinalIgnoreCase ) );
		if ( station.IsValid() && Operator.CurrentEquipment != station ) Operator.Inventory.Switch( station );

		IsLinked = true;
		Piloted = this;
		_sinceLinked = 0;
		_lastHealth = Operator.HealthComponent.Health;
		_yawTarget = CameraYaw;
		_pitchTarget = GimbalPitch;

		// The feed's camera first, then the body's off: only one main camera draws, and Scene.Camera follows at once.
		CreateCamera();
		_bodyCamera = Operator.CameraController.IsValid() ? Operator.CameraController.Camera : null;
		if ( _bodyCamera.IsValid() ) _bodyCamera.Enabled = false;
	}

	/// <summary>Back to the body. The drone holds where it is.</summary>
	public void Unlink()
	{
		if ( Piloted == this )
		{
			Piloted = null;
			_sinceUnlinked = 0;
		}
		if ( _bodyCamera.IsValid() ) _bodyCamera.Enabled = true;
		_bodyCamera = null;
		if ( FeedCamera.IsValid() ) FeedCamera.Enabled = false;
		FeedCamera = null;
		_cameraObject?.Destroy();
		_cameraObject = null;
		if ( !IsProxy && IsLinked ) IsLinked = false;
	}

	/// <summary>Drop whatever drone this pawn's machine is flying, e.g. when a flash hits the body.</summary>
	public static void DropLink( PlayerPawn pawn )
	{
		if ( IsPiloting( pawn ) ) Piloted.Unlink();
	}

	private ColorAdjustments _feedColorAdjustments;

	private void CreateCamera()
	{
		_cameraObject = new GameObject( true, $"{DisplayName} Feed" );
		_cameraObject.Flags |= GameObjectFlags.NotSaved;
		_cameraObject.NetworkMode = NetworkMode.Never;
		_cameraObject.WorldTransform = FeedTransform();

		var camera = _cameraObject.Components.Create<CameraComponent>( false );
		camera.IsMainCamera = true;
		camera.Priority = 50;
		camera.FovAxis = CameraComponent.Axis.Horizontal;
		camera.FieldOfView = HorizontalFieldOfView;
		camera.ZNear = CameraNearPlane;
		camera.ZFar = 100000f;
		// The body's "viewer" tag isn't excluded: from up here the operator is just another soldier.
		camera.RenderExcludeTags.Add( "invis" );
		// Nor is the drone itself drawn. The lens hangs under the nose, inside the rotors' reach: tilted into a flight,
		// looking up, or turned faster than the airframe follows, its own props and arms filled the picture, and the nose
		// came within an inch of the lens, through the near plane.
		camera.RenderExcludeTags.Add( OwnDroneTag );

		// The same picture as the body's camera, so the map's lighting looks the same.
		var source = Operator.CameraController?.Camera;
		if ( source.IsValid() )
		{
			camera.BackgroundColor = source.BackgroundColor;
			CameraPostProcess.Copy<Bloom>( source.GameObject, _cameraObject );
			CameraPostProcess.Copy<Tonemapping>( source.GameObject, _cameraObject );
			CameraPostProcess.Copy<Sharpen>( source.GameObject, _cameraObject );
			CameraPostProcess.Copy<AmbientOcclusion>( source.GameObject, _cameraObject );
			CameraPostProcess.Copy<Vignette>( source.GameObject, _cameraObject );
			_feedColorAdjustments = CameraPostProcess.Copy<ColorAdjustments>( source.GameObject, _cameraObject );
		}

		camera.Enabled = true;
		FeedCamera = camera;
	}

	/// <summary>The camera behind the lens: the gimbal holds it level whatever the airframe does.</summary>
	public Transform FeedTransform()
	{
		var rotation = Rotation.From( GimbalPitch, CameraYaw, 0f );
		var pivot = Gimbal.IsValid() ? Gimbal.WorldPosition : WorldPosition;
		return new Transform( pivot + rotation * LensOffset, rotation );
	}

	// ---- Every machine ---------------------------------------------------------------------------------------------

	protected override void OnUpdate()
	{
		if ( !IsProxy )
		{
			Simulate( MathF.Min( Time.Delta, 0.05f ) );
			// Only the pilot's own feed leaves it out (the feed is made on the owner's machine): it still casts its shadow,
			// and everyone else sees it.
			Tags.Set( OwnDroneTag, FeedCamera.IsValid() );
		}

		if ( Gimbal.IsValid() )
			Gimbal.WorldRotation = Rotation.From( GimbalPitch, CameraYaw, 0f );

		UpdateRotors();
		UpdateSound();

		if ( FeedCamera.IsValid() )
		{
			_cameraObject.WorldTransform = FeedTransform();
			FeedCamera.FieldOfView = HorizontalFieldOfView;
			var source = _bodyCamera.IsValid() ? _bodyCamera.GetComponent<ColorAdjustments>( true ) : null;
			CameraPostProcess.SyncColor( source, _feedColorAdjustments );
		}
	}

	private void UpdateRotors()
	{
		var running = State is not (FlightState.Wreck or FlightState.Falling);
		var target = running ? MathF.Sqrt( MathF.Max( Throttle, 0f ) ) * HoverRpm : 0f;
		// Motors spin up and down in a fraction of a second; a dead one coasts down slower.
		_rpm = _rpm.LerpTo( target, Time.Delta * (running ? 6f : 1.5f) );
		if ( _rotors is null ) return;
		foreach ( var rotor in _rotors )
			if ( rotor.IsValid() ) rotor.Turn( _rpm, Time.Delta );
	}

	private void UpdateSound()
	{
		if ( RotorSound is null || Application.IsDedicatedServer ) return;
		var fraction = _rpm / HoverRpm;
		if ( fraction < 0.05f )
		{
			if ( _rotorSound.IsValid() ) _rotorSound.Stop( 0.3f );
			_rotorSound = null;
			return;
		}
		if ( !_rotorSound.IsValid() || _rotorSound.Finished )
			_rotorSound = Sound.Play( RotorSound, WorldPosition );
		_rotorSound.Position = WorldPosition;
		// The blade-pass tone goes with the rotor speed; the sound's power rises much faster than that.
		_rotorSound.Pitch = Math.Clamp( fraction, 0.3f, 1.4f );
		_rotorSound.Volume = Math.Clamp( fraction * fraction * fraction, 0f, 1.6f );
	}

	// ---- Flying (the operator's machine) ---------------------------------------------------------------------------

	private void Simulate( float dt )
	{
		_stateTime += dt;
		if ( _linkOnStart && _sinceLaunched >= LinkDelay )
		{
			_linkOnStart = false;
			Link();
		}
		CheckOperator();
		// Death during the hand release must land the aircraft even before its feed opens.
		if ( HandLaunched && (!Operator.IsValid() || Operator.HealthComponent.State != LifeState.Alive)
			&& State is FlightState.Spooling or FlightState.TakingOff or FlightState.Flying )
			BeginLanding( true );

		var powered = State is FlightState.Spooling or FlightState.TakingOff or FlightState.Flying or FlightState.Landing;
		if ( powered )
		{
			Battery = MathF.Max( 0f, Battery - dt / MathF.Max( BatterySeconds, 0.01f ) );
			if ( Battery <= 0f && State != FlightState.Landing ) BeginLanding( true );
		}

		if ( IsDestroyed && State is not (FlightState.Falling or FlightState.Wreck) )
		{
			Unlink();
			SetState( FlightState.Falling );
			_spin = new Vector3( Game.Random.Float( -200f, 200f ), Game.Random.Float( -200f, 200f ), Game.Random.Float( -400f, 400f ) );
		}

		if ( IsLinked ) ReadCameraInput( dt );

		switch ( State )
		{
			case FlightState.Spooling:
				Throttle = Throttle.LerpTo( 0.12f, dt * 4f );
				if ( _stateTime >= SpoolSeconds ) SetState( FlightState.TakingOff );
				break;
			case FlightState.Falling:
				Fall( dt );
				return;
			case FlightState.Wreck:
				Throttle = 0f;
				if ( _stateTime > 15f ) GameObject.Destroy();
				return;
			case FlightState.Landed:
				Throttle = Throttle.LerpTo( 0f, dt * 2f );
				_velocity = 0f;
				// Out of battery or with nobody to fly it, it's done: the operator's tablet goes with it.
				if ( (Battery <= 0f || !Operator.IsValid() || Operator.HealthComponent.State != LifeState.Alive) && _stateTime > 2.5f )
				{
					RequestRetire();
					GameObject.Destroy();
					return;
				}
				if ( IsLinked && Battery > 0f && Input.Pressed( "Jump" ) ) SetState( FlightState.Spooling );
				break;
		}

		if ( State is FlightState.Spooling or FlightState.Landed )
		{
			_lastVelocity = _velocity;
			return;
		}

		Fly( dt );
	}

	private void CheckOperator()
	{
		if ( !IsLinked ) return;
		if ( !Operator.IsValid() || Operator.HealthComponent.State != LifeState.Alive )
		{
			Unlink();
			BeginLanding( true );
			return;
		}

		// Hurt, the operator looks up from the screen.
		var health = Operator.HealthComponent.Health;
		if ( health < _lastHealth - 0.5f )
		{
			Unlink();
			return;
		}
		_lastHealth = health;

		if ( Input.Pressed( "Use" ) && _sinceLinked > 0.3f ) Unlink();
	}

	private void ReadCameraInput( float dt )
	{
		// Mouse look turns the camera; at long zoom it's slowed by the zoom, as a gimbal's stick is.
		var look = Input.AnalogLook;
		_yawTarget += look.yaw / Zoom;
		_pitchTarget = (_pitchTarget + look.pitch / Zoom).Clamp( MinGimbalPitch, MaxGimbalPitch );

		// The gimbal's motors turn it at most 180 degrees a second.
		var slew = 180f * dt;
		CameraYaw += Math.Clamp( Angles.NormalizeAngle( _yawTarget - CameraYaw ), -slew, slew );
		GimbalPitch += Math.Clamp( _pitchTarget - GimbalPitch, -slew, slew );
		_yawTarget = CameraYaw + Angles.NormalizeAngle( _yawTarget - CameraYaw );

		if ( _sinceLinked < 0.3f ) return;
		var step = 0;
		if ( Input.MouseWheel.y > 0f || Input.Pressed( "Attack1" ) ) step = 1;
		else if ( Input.MouseWheel.y < 0f || Input.Pressed( "Attack2" ) ) step = -1;
		if ( step == 0 ) return;
		var steps = AvailableZoomSteps;
		var index = Array.FindIndex( steps, z => z >= Zoom - 0.01f );
		if ( index < 0 ) index = steps.Length - 1;
		Zoom = steps[Math.Clamp( index + step, 0, steps.Length - 1 )];
	}

	private void Fly( float dt )
	{
		var height = WorldPosition.z - _launchZ;
		var groundGap = GroundGap();
		Vector3 wish = 0f;
		float climb = 0f;

		switch ( State )
		{
			case FlightState.TakingOff:
				climb = TakeoffHeight - groundGap > 4f ? ClimbRate * 0.6f : 0f;
				if ( groundGap >= TakeoffHeight - 4f || _stateTime > 6f ) SetState( FlightState.Flying );
				break;
			case FlightState.Landing:
				// Slower the nearer the ground, as an autoland's final metres are.
				climb = -Math.Clamp( groundGap * 1.2f, 0.5f * Metre, DescentRate );
				if ( IsLinked && !_forcedLanding )
				{
					wish = StickVelocity();
					if ( Input.Pressed( "Jump" ) ) SetState( FlightState.Flying );
				}
				break;
			case FlightState.Flying:
				if ( IsLinked && Battery > 0f )
				{
					wish = StickVelocity();
					if ( Input.Down( "Jump" ) ) climb = ClimbRate;
					else if ( Input.Down( "Duck" ) ) climb = -DescentRate;
					// Held down at the ground, it lands.
					if ( Input.Down( "Duck" ) && groundGap < 8f ) BeginLanding( false );
				}
				break;
		}

		if ( height >= Ceiling && climb > 0f ) climb = 0f;

		// Position hold: the controller drives the velocity to the sticks' as fast as the airframe can accelerate.
		var horizontal = _velocity.WithZ( 0f );
		var change = wish - horizontal;
		var maxChange = Acceleration * dt;
		if ( change.Length > maxChange ) change = change.Normal * maxChange;
		horizontal += change;
		var vertical = _velocity.z + Math.Clamp( climb - _velocity.z, -VerticalAcceleration * dt, VerticalAcceleration * dt );
		_velocity = horizontal.WithZ( vertical );

		var touchedDown = Move( _velocity * dt );
		if ( State == FlightState.Landing && touchedDown ) SetState( FlightState.Landed );

		UpdateAttitude( dt );
		_lastVelocity = _velocity;
	}

	private Vector3 StickVelocity()
	{
		var move = Input.AnalogMove;
		var heading = Rotation.FromYaw( CameraYaw );
		var wish = heading.Forward * move.x + heading.Left * move.y;
		if ( wish.Length > 1f ) wish = wish.Normal;
		return wish * (Input.Down( "Run" ) ? SportSpeed : CruiseSpeed);
	}

	/// <summary>
	/// A multirotor leans into its thrust: its rotors push along its up axis, so to accelerate (and to hold speed
	/// against drag) it tilts until thrust less gravity is that acceleration.
	/// </summary>
	private void UpdateAttitude( float dt )
	{
		var accel = dt > 0f ? (_velocity - _lastVelocity) / dt : Vector3.Zero;
		var drag = _velocity * _velocity.Length * DragPerInch;
		var thrust = accel + drag + Vector3.Up * Gravity;
		Throttle = Throttle.LerpTo( thrust.Length / Gravity, dt * 8f );

		var up = thrust.Normal;
		var tilt = MathF.Acos( Math.Clamp( up.z, -1f, 1f ) ) * 180f / MathF.PI;
		if ( tilt > MaxTilt )
		{
			var flat = up.WithZ( 0f ).Normal;
			var radians = MaxTilt * MathF.PI / 180f;
			up = flat * MathF.Sin( radians ) + Vector3.Up * MathF.Cos( radians );
		}

		// The airframe turns after the camera, at most 120 degrees a second.
		var yawStep = 120f * dt;
		_bodyYaw += Math.Clamp( Angles.NormalizeAngle( CameraYaw - _bodyYaw ), -yawStep, yawStep );

		var target = Rotation.FromToRotation( Vector3.Up, up ) * Rotation.FromYaw( _bodyYaw );
		var rotation = Rotation.Slerp( WorldRotation, target, Math.Clamp( dt * 10f, 0f, 1f ) );
		if ( RotateCollisionHull )
		{
			// Turning the long tail beside a wall must not grow the collision box into that wall.
			var room = Scene.Trace.Box( CollisionHullFor( rotation ), WorldPosition, WorldPosition )
				.IgnoreGameObjectHierarchy( GameObject ).WithoutTags( "trigger", "ragdoll" ).Run();
			if ( room.StartedSolid ) return;
		}
		WorldRotation = rotation;
	}

	private float GroundGap()
	{
		var start = WorldPosition;
		var trace = Scene.Trace.Ray( start, start + Vector3.Down * 2000f )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "ragdoll", "player", "movement" )
			.Run();
		var bottom = start.z + CollisionHullFor( WorldRotation ).Mins.z;
		return trace.Hit ? MathF.Max( 0f, bottom - trace.EndPosition.z ) : 2000f;
	}

	/// <summary>Slide along what it hits. Returns whether it came down on something it could stand on.</summary>
	private bool Move( Vector3 delta )
	{
		var position = WorldPosition;
		var landed = false;
		for ( var i = 0; i < 3 && delta.LengthSquared > 0.0001f; i++ )
		{
			var trace = Scene.Trace.Box( CollisionHullFor( WorldRotation ), position, position + delta )
				.IgnoreGameObjectHierarchy( GameObject )
				.WithoutTags( "trigger", "ragdoll" )
				.Run();
			if ( trace.StartedSolid )
			{
				if ( RotateCollisionHull ) { _velocity = 0f; break; }
				position += delta;
				break;
			}

			position = trace.EndPosition;
			if ( !trace.Hit ) break;

			var into = -Vector3.Dot( _velocity, trace.Normal );
			if ( into > CrashSpeed && _sinceImpact > 0.5f )
			{
				_sinceImpact = 0;
				ReportImpact( into, position );
			}
			if ( trace.Normal.z > 0.7f && _velocity.z <= 0f ) landed = true;

			var remaining = delta * (1f - trace.Fraction);
			_velocity -= trace.Normal * MathF.Min( 0f, Vector3.Dot( _velocity, trace.Normal ) );
			delta = remaining - trace.Normal * Vector3.Dot( remaining, trace.Normal );
			position += trace.Normal * 0.1f;
		}
		WorldPosition = position;
		return landed;
	}

	private void Fall( float dt )
	{
		Throttle = 0f;
		_velocity += Vector3.Down * Gravity * dt;
		_velocity -= _velocity * _velocity.Length * DragPerInch * dt;
		_tumble = Rotation.From( new Angles( _spin.x, _spin.z, _spin.y ) * dt );
		WorldRotation = WorldRotation * _tumble;
		if ( Move( _velocity * dt ) || _stateTime > 20f )
		{
			_velocity = 0f;
			SetState( FlightState.Wreck );
		}
	}

	private void BeginLanding( bool forced )
	{
		if ( State is FlightState.Landed or FlightState.Falling or FlightState.Wreck ) return;
		_forcedLanding = forced;
		if ( State == FlightState.Spooling && !HandLaunched )
		{
			SetState( FlightState.Landed );
			return;
		}
		SetState( FlightState.Landing );
	}

	private void SetState( FlightState state )
	{
		State = state;
		_stateTime = 0f;
	}

	// ---- The host --------------------------------------------------------------------------------------------------

	protected override void OnFixedUpdate()
	{
		if ( !Networking.IsHost || IsDestroyed ) return;
		if ( State is FlightState.Wreck or FlightState.Falling ) return;
		if ( _sinceScan < 0.5f ) return;
		_sinceScan = 0;
		Scan();
	}

	public void OnDamage( in Sandbox.DamageInfo info )
	{
		if ( !Networking.IsHost || IsDestroyed ) return;

		var attacker = info.Attacker?.GetComponentInParent<PlayerPawn>();
		// The operator's teammates hold their fire on their own drone.
		if ( attacker.IsValid() && attacker != Operator && !GameUtils.IsFreeForAllMode && attacker.Team == ReconTeam ) return;

		var damage = info.Damage;
		if ( damage <= 0f ) return;
		Integrity -= damage;
		var destroyed = Integrity <= 0f;
		if ( attacker.IsValid() ) ShowHit( attacker, destroyed );
		if ( !destroyed ) return;

		IsDestroyed = true;
		Contacts.Clear();
		RemoveTablet();
		Sparks( info.Position == default ? WorldPosition : info.Position );
	}

	[Rpc.Host]
	private void ReportImpact( float speed, Vector3 position )
	{
		if ( IsDestroyed ) return;
		var damage = (speed - ImpactDamageThreshold) * 0.25f;
		if ( damage <= 0f ) return;
		Integrity -= damage;
		Sparks( position );
		if ( Integrity > 0f ) return;
		IsDestroyed = true;
		Contacts.Clear();
		RemoveTablet();
	}

	[Rpc.Host]
	private void RequestRetire()
	{
		RemoveTablet();
	}

	/// <summary>With the drone gone, its tablet has nothing to fly.</summary>
	private void RemoveTablet()
	{
		if ( !Networking.IsHost || !Operator.IsValid() || !Operator.Inventory.IsValid() ) return;
		foreach ( var equipment in Operator.Inventory.Equipment.ToArray() )
			if ( equipment.IsValid() && string.Equals( equipment.Resource?.ResourcePath, StationResourcePath, StringComparison.OrdinalIgnoreCase ) )
				Operator.Inventory.RemoveWeapon( equipment );
	}

	[Rpc.Broadcast]
	private void ShowHit( PlayerPawn attacker, bool destroyed )
	{
		if ( attacker.IsValid() && attacker.IsViewer )
			Crosshair.Instance?.ShowHit( destroyed, false );
	}

	[Rpc.Broadcast]
	private void Sparks( Vector3 position )
	{
		if ( Application.IsDedicatedServer || SparksPrefab is null ) return;
		var prefab = SceneUtility.GetPrefabScene( SparksPrefab );
		if ( !prefab.IsValid() ) return;
		var sparks = prefab.Clone( new CloneConfig { StartEnabled = false } );
		sparks.WorldPosition = position;
		sparks.NetworkMode = NetworkMode.Never;
		sparks.Enabled = true;
		sparks.DestroyAsync( 2f );
	}

	/// <summary>Who's in the camera's picture, near enough to make out, and not hidden.</summary>
	private void Scan()
	{
		if ( !Operator.IsValid() ) return;
		var camera = FeedTransform();
		var tanH = MathF.Tan( HorizontalFieldOfView * 0.5f * MathF.PI / 180f );
		var tanV = tanH * 9f / 16f;
		var range = SpotRange * Zoom;

		foreach ( var pawn in Scene.GetAllComponents<PlayerPawn>() )
		{
			if ( !pawn.HealthComponent.IsValid() || pawn.HealthComponent.State != LifeState.Alive ) continue;
			if ( pawn.GetComponent<PlayerPerks>()?.HasPerk( "ghost" ) == true ) continue;
			if ( !IsEnemy( pawn.GameObject, pawn.Team ) ) continue;
			if ( Sees( camera, tanH, tanV, range, pawn.GameObject, pawn.WorldPosition ) ) _lastSeen[pawn.GameObject.Id] = 0;
		}
		foreach ( var bot in Scene.GetAllComponents<LightweightCombatBot>() )
		{
			if ( !bot.IsAlive || !IsEnemy( bot.GameObject, bot.Team ) ) continue;
			if ( Sees( camera, tanH, tanV, range, bot.GameObject, bot.WorldPosition ) ) _lastSeen[bot.GameObject.Id] = 0;
		}

		// A contact stays marked a second after it's last seen, as an operator's eye holds it.
		foreach ( var id in _lastSeen.Where( x => x.Value > 1f ).Select( x => x.Key ).ToArray() ) _lastSeen.Remove( id );
		foreach ( var old in Contacts.Where( id => !_lastSeen.ContainsKey( id ) ).ToArray() ) Contacts.Remove( old );
		foreach ( var id in _lastSeen.Keys ) if ( !Contacts.Contains( id ) ) Contacts.Add( id );
	}

	private bool IsEnemy( GameObject target, Team team ) => target != Operator.GameObject
		&& (GameUtils.IsFreeForAllMode || team != ReconTeam);

	private bool Sees( Transform camera, float tanH, float tanV, float range, GameObject target, Vector3 feet )
	{
		foreach ( var point in new[] { feet + Vector3.Up * 40f, feet + Vector3.Up * 62f } )
		{
			var local = camera.PointToLocal( point );
			if ( local.x <= 1f || local.x > range ) continue;
			if ( MathF.Abs( local.y ) > local.x * tanH || MathF.Abs( local.z ) > local.x * tanV ) continue;
			var blocked = Scene.Trace.Ray( camera.Position, point )
				.IgnoreGameObjectHierarchy( GameObject )
				.IgnoreGameObjectHierarchy( target )
				.WithoutTags( "trigger", "playerclip", "glass", "movement", "ragdoll" )
				.Run().Hit;
			if ( !blocked ) return true;
		}
		return false;
	}

	public IEnumerable<GameObject> ContactObjects => Contacts
		.Select( id => Scene.Directory.FindByGuid( id ) )
		.Where( go => go.IsValid() );

	public bool IsFriendlyTo( Pawn viewer ) => viewer.IsValid()
		&& (GameUtils.IsFreeForAllMode ? viewer == Operator : viewer.Team == ReconTeam && ReconTeam != Team.Unassigned);

	public static bool Reveals( GameObject target, Pawn viewer ) => target.IsValid() && viewer.IsValid()
		&& target.Scene.GetAllComponents<ReconOctocopter>().Any( drone => !drone.IsDestroyed
			&& drone.IsFriendlyTo( viewer ) && drone.Contacts.Contains( target.Id ) );

	// ---- Rounds and the radar --------------------------------------------------------------------------------------

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent e ) => Retire();
	void IGameEventHandler<BetweenRoundCleanupEvent>.OnGameEvent( BetweenRoundCleanupEvent e ) => Retire();

	private void Retire()
	{
		if ( !IsProxy ) GameObject.Destroy();
	}

	bool IMinimapElement.IsVisible( Pawn viewer ) => !IsDestroyed && IsFriendlyTo( viewer );
	Vector3 IMinimapElement.WorldPosition => WorldPosition;
	string IMinimapIcon.IconPath => IconPath;
	string ICustomMinimapIcon.CustomStyle => $"background-image-tint: {ReconTeam.GetColor().Hex}";
}
