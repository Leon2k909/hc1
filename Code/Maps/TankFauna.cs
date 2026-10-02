namespace Facepunch;

/// <summary>
/// The animals in one of a map's aquarium tanks: reef sharks, manta rays and schools of small fish, swimming about on
/// their own on every machine (they're scenery, so nothing is networked). Each one stays inside the tank's water: the
/// water's shape less the rocks and kelp in it (<see cref="Obstacles"/>), kept a body's reach from all of it, so no
/// nose, fin or wingtip ever goes through the glass, a wall or a rock. Their bodies swim in their material
/// (shaders/hc1_fish.shader). Reef Hall's tanks get theirs from Tools/reefhall_map.py.
///
/// Everything here is in the object's own space: the tank's middle at its origin, its floor and water surface at
/// -Size.z / 2 and +Size.z / 2. They swim in the editor too, so a tank can be judged while the map is worked on.
/// </summary>
public sealed class TankFauna : Component, Component.ExecuteInEditor
{
	public enum TankShape
	{
		/// <summary>A box of <see cref="Size"/>.</summary>
		Box,

		/// <summary>An upright cylinder: Size.x across, Size.z high.</summary>
		Cylinder,
	}

	[Property] public TankShape Shape { get; set; }

	/// <summary>The water's size, from the sand (over the coral) to just under the surface.</summary>
	[Property] public Vector3 Size { get; set; } = new( 200, 200, 200 );

	/// <summary>A glass tube running through the water along the local X axis (the Tunnel Hall's vault): no water
	/// within this of the line through <see cref="HoleCentre"/>. 0: none.</summary>
	[Property] public float HoleRadius { get; set; }

	[Property] public Vector3 HoleCentre { get; set; }

	/// <summary>Rocks, coral and kelp, "x y z radius height taper" each, separated by ';': a cone standing on x y z,
	/// this wide at its foot and narrowing by taper (a share of it) to its top. A negative taper widens it, as kelp
	/// fans out from its root.</summary>
	[Property, Hide] public string Obstacles { get; set; }

	[Property] public int Sharks { get; set; }
	[Property] public int Rays { get; set; }
	[Property] public int Schools { get; set; }
	[Property] public int SchoolSize { get; set; } = 10;

	/// <summary>The schools' fish, each school one of these, in turn.</summary>
	[Property] public List<string> SchoolModels { get; set; } = [ "models/maps/reefhall/fauna/yellow_tang.vmdl", "models/maps/reefhall/fauna/chromis.vmdl" ];

	[Property] public string SharkModel { get; set; } = "models/maps/reefhall/fauna/reef_shark.vmdl";
	[Property] public string RayModel { get; set; } = "models/maps/reefhall/fauna/manta_ray.vmdl";

	[Property] public int Seed { get; set; }

	/// <summary>Beyond this from the camera nothing small is drawn, and nothing moves more than 4 times a second.</summary>
	[Property] public float FarDistance { get; set; } = 3000f;

	// A kind of animal: ( how far its body reaches from its middle sideways and lengthways, up and down, its cruising
	// speed in units a second, how fast it turns in degrees a second, how steeply it climbs, how far it banks in a turn )
	private sealed record Kind( float Reach, float ReachUp, float Speed, float TurnRate, float Climb, float Bank );

	// A grey reef shark 1.8 m long cruises at ~1 m/s; a 3.5 m manta glides at ~0.8 m/s; tangs and chromis potter about.
	private static readonly Kind SharkKind = new( 40f, 22f, 42f, 28f, 0.25f, 18f );
	private static readonly Kind RayKind = new( 74f, 40f, 30f, 20f, 0.2f, 24f );
	private static readonly Kind SmallKind = new( 6f, 5f, 16f, 160f, 0.45f, 10f );

	private sealed class Swimmer
	{
		public Kind Kind;
		public SceneObject Body;
		public Vector3 Position;
		public Vector3 Forward = Vector3.Forward;
		public float Speed;
		public float Roll;
		public float Scale = 1f;
		public Vector3 Target;
		public float RetargetAt;
		public float Blocked;

		// School members: their leader and their place beside it (in the leader's frame)
		public Swimmer Leader;
		public Vector3 Offset;
		public float Wobble;
	}

	private readonly List<Swimmer> _swimmers = [];
	private readonly List<(Vector3 Base, float Radius, float Height, float Taper)> _obstacles = [];
	private Random _random;
	private float _time;
	private float _farStep;

	protected override void OnEnabled()
	{
		if ( Application.IsDedicatedServer )
			return;

		_random = new Random( Seed );
		ParseObstacles();

		for ( var k = 0; k < Sharks; k++ )
			Spawn( SharkKind, SharkModel, _random.Float( 0.92f, 1.1f ) );
		for ( var k = 0; k < Rays; k++ )
			Spawn( RayKind, RayModel, _random.Float( 0.9f, 1.08f ) );

		for ( var s = 0; s < Schools; s++ )
		{
			var model = SchoolModels.Count > 0 ? SchoolModels[s % SchoolModels.Count] : null;
			if ( string.IsNullOrEmpty( model ) )
				continue;

			// The leader is only a point the school follows, with room round it for most of the school (each fish keeps
			// its own room too).
			var radius = SmallKind.Reach * 2.2f * MathF.Cbrt( Math.Max( SchoolSize, 1 ) );
			var leader = Spawn( SmallKind with { Reach = radius * 0.6f, ReachUp = radius * 0.3f, Speed = 14f, TurnRate = 55f },
				null, 1f );
			if ( leader is null )
				continue;

			for ( var k = 0; k < SchoolSize; k++ )
			{
				var offset = new Vector3( _random.Float( -1f, 1f ), _random.Float( -1f, 1f ), _random.Float( -0.5f, 0.5f ) ) * radius;
				var fish = Spawn( SmallKind, model, _random.Float( 0.85f, 1.15f ), leader.Position + offset );
				if ( fish is null )
					continue;
				fish.Leader = leader;
				fish.Offset = offset;
				fish.Wobble = _random.Float( 0f, 100f );
				fish.Forward = leader.Forward;
			}
		}
	}

	protected override void OnDisabled()
	{
		foreach ( var swimmer in _swimmers )
			swimmer.Body?.Delete();
		_swimmers.Clear();
		_obstacles.Clear();
	}

	private void ParseObstacles()
	{
		_obstacles.Clear();
		if ( string.IsNullOrWhiteSpace( Obstacles ) )
			return;

		foreach ( var entry in Obstacles.Split( ';', StringSplitOptions.RemoveEmptyEntries ) )
		{
			var parts = entry.Split( ' ', StringSplitOptions.RemoveEmptyEntries );
			if ( parts.Length < 5 )
				continue;
			var v = parts.Select( x => float.Parse( x, System.Globalization.CultureInfo.InvariantCulture ) ).ToArray();
			_obstacles.Add( (new Vector3( v[0], v[1], v[2] ), v[3], v[4], v.Length > 5 ? v[5] : 0.5f) );
		}
	}

	private Swimmer Spawn( Kind kind, string modelPath, float scale, Vector3? near = null )
	{
		var swimmer = new Swimmer { Kind = kind with { Reach = kind.Reach * scale, ReachUp = kind.ReachUp * scale }, Scale = scale };
		swimmer.Speed = kind.Speed * _random.Float( 0.85f, 1.15f );

		if ( near is { } point && IsFree( point, swimmer.Kind ) )
			swimmer.Position = point;
		else if ( !TryPickPoint( swimmer.Kind, out swimmer.Position ) )
			return null;

		var heading = _random.Float( 0f, 360f );
		swimmer.Forward = Rotation.FromYaw( heading ).Forward;
		swimmer.Target = swimmer.Position;
		swimmer.RetargetAt = 0f;

		if ( modelPath is not null )
		{
			var model = Model.Load( modelPath );
			if ( model is null || model.IsError )
				return null;
			swimmer.Body = new SceneObject( Scene.SceneWorld, model, Transform.World );
			swimmer.Body.Flags.CastShadows = false;
		}

		_swimmers.Add( swimmer );
		return swimmer;
	}

	protected override void OnUpdate()
	{
		if ( _swimmers.Count == 0 )
			return;

		var dt = Math.Min( Time.Delta, 0.1f );
		var camera = Scene.Camera;
		var far = camera.IsValid() && camera.WorldPosition.Distance( WorldPosition ) > FarDistance + Math.Max( Size.x, Size.y );

		// Far away, it all moves a few times a second, and the small fish aren't drawn.
		if ( far )
		{
			_farStep += dt;
			if ( _farStep < 0.25f )
				return;
			dt = Math.Min( _farStep, 0.5f );
			_farStep = 0f;
		}

		_time += dt;
		var world = WorldTransform;

		// Leaders first, so their schools follow where they are now.
		foreach ( var swimmer in _swimmers )
		{
			if ( swimmer.Leader is null )
				Cruise( swimmer, dt );
		}

		foreach ( var swimmer in _swimmers )
		{
			if ( swimmer.Leader is not null )
				Follow( swimmer, dt );

			if ( swimmer.Body is null )
				continue;

			swimmer.Body.RenderingEnabled = !far || swimmer.Kind.Reach > 20f;
			var rotation = Rotation.LookAt( swimmer.Forward, Vector3.Up ) * Rotation.FromRoll( swimmer.Roll );
			swimmer.Body.Transform = new Transform( world.PointToWorld( swimmer.Position ), world.Rotation * rotation, swimmer.Scale );
		}
	}

	/// <summary>A shark, a ray or a school's leader: swims at a point in the water, then picks another.</summary>
	private void Cruise( Swimmer swimmer, float dt )
	{
		var kind = swimmer.Kind;
		var toTarget = swimmer.Target - swimmer.Position;
		if ( _time >= swimmer.RetargetAt || toTarget.Length < kind.Reach + 30f || swimmer.Blocked > 2.5f )
		{
			if ( TryPickPoint( kind, out var target, swimmer.Position ) )
				swimmer.Target = target;
			swimmer.RetargetAt = _time + _random.Float( 8f, 20f );
			swimmer.Blocked = 0f;
			toTarget = swimmer.Target - swimmer.Position;
		}

		var desired = Level( toTarget.Normal, kind.Climb );

		// Feel ahead: where it will be in a second and a bit, and its nose beyond that. If that isn't open water, look
		// round for the way that is, nearest where it wants to go, and turn into it hard and slowed down.
		var look = swimmer.Speed * 1.3f + kind.Reach * 0.5f;
		var turn = 1f;
		var pace = 1f;
		if ( !IsFree( swimmer.Position + swimmer.Forward * look, kind ) )
		{
			swimmer.Blocked += dt;
			turn = 2f;
			pace = 0.5f;
			var best = -swimmer.Forward;
			var bestScore = float.MinValue;
			foreach ( var (yaw, pitch) in Fan )
			{
				var climb = pitch * kind.Climb;
				var flat = MathF.Sqrt( 1f - climb * climb );
				var direction = new Vector3( yaw.x * flat, yaw.y * flat, climb );
				var score = Vector3.Dot( direction, desired ) + 0.5f * Vector3.Dot( direction, swimmer.Forward );
				if ( score > bestScore && IsFree( swimmer.Position + direction * look, kind ) )
				{
					best = direction;
					bestScore = score;
				}
			}
			desired = best;
		}

		Steer( swimmer, Level( desired, kind.Climb ), dt, turn );
		Move( swimmer, swimmer.Speed * pace, dt );
	}

	// The ways a swimmer looks round in when the water ahead is blocked: every 15 degrees round, level, a little up and
	// a little down (a share of its climb).
	private static readonly (Vector2 Yaw, float Pitch)[] Fan = Enumerable.Range( 0, 24 )
		.SelectMany( k => new[] { 0f, 0.6f, -0.6f }.Select( pitch =>
			(new Vector2( MathF.Cos( k * 15f * MathF.PI / 180f ), MathF.Sin( k * 15f * MathF.PI / 180f ) ), pitch) ) )
		.ToArray();

	/// <summary>A fish in a school: keeps its place beside the leader, a little loosely, swimming the way it goes.</summary>
	private void Follow( Swimmer swimmer, float dt )
	{
		var leader = swimmer.Leader;
		var frame = Rotation.LookAt( leader.Forward.WithZ( 0 ).Normal, Vector3.Up );
		var drift = new Vector3( MathF.Sin( _time * 0.37f + swimmer.Wobble ), MathF.Sin( _time * 0.29f + swimmer.Wobble * 1.7f ),
			MathF.Sin( _time * 0.23f + swimmer.Wobble * 2.3f ) * 0.4f ) * SmallKind.Reach * 1.5f;
		var place = leader.Position + frame * ( swimmer.Offset + drift );

		var toPlace = place - swimmer.Position;
		var distance = toPlace.Length;
		var desired = ( leader.Forward + toPlace / Math.Max( SmallKind.Reach * 3f, 1f ) ).Normal;
		var push = Push( swimmer.Position + swimmer.Forward * swimmer.Kind.Reach * 2f, swimmer.Kind );
		if ( push.LengthSquared > 0.01f )
			desired = ( desired + push.Normal * 2f ).Normal;

		// Catch up when it has fallen behind, ease off when it's ahead.
		var along = Vector3.Dot( toPlace, leader.Forward );
		var speed = leader.Speed * Math.Clamp( 1f + along / ( SmallKind.Reach * 4f ), 0.6f, 2.2f );
		if ( distance < SmallKind.Reach )
			speed = MathX.Lerp( speed, leader.Speed, 0.5f );

		Steer( swimmer, Level( desired, swimmer.Kind.Climb ), dt );
		Move( swimmer, speed, dt );
	}

	private static Vector3 Level( Vector3 direction, float climb )
	{
		var z = Math.Clamp( direction.z, -climb, climb );
		var flat = direction.WithZ( 0 );
		if ( flat.LengthSquared < 0.0001f )
			flat = Vector3.Forward;
		return ( flat.Normal * MathF.Sqrt( 1f - z * z ) ).WithZ( z );
	}

	private static void Steer( Swimmer swimmer, Vector3 desired, float dt, float sharpness = 1f )
	{
		var cos = Math.Clamp( Vector3.Dot( swimmer.Forward, desired ), -1f, 1f );
		var angle = MathF.Acos( cos ) * ( 180f / MathF.PI );
		var step = swimmer.Kind.TurnRate * sharpness * dt;
		var before = swimmer.Forward;
		if ( angle > 0.01f )
		{
			var t = Math.Min( 1f, step / angle );
			swimmer.Forward = Vector3.Lerp( swimmer.Forward, desired, t ).Normal;
		}

		// Bank into the turn, as a ray or a shark does; ease out of it on the straight.
		var turn = Vector3.Cross( before, swimmer.Forward ).z / Math.Max( dt, 0.0001f ) * ( 180f / MathF.PI );
		var bank = Math.Clamp( -turn / Math.Max( swimmer.Kind.TurnRate, 1f ), -1f, 1f ) * swimmer.Kind.Bank;
		swimmer.Roll = MathX.Lerp( swimmer.Roll, bank, Math.Min( 1f, dt * 1.5f ) );
	}

	private void Move( Swimmer swimmer, float speed, float dt )
	{
		var from = swimmer.Position;
		var before = Push( from, swimmer.Kind ).Length;
		swimmer.Position += swimmer.Forward * speed * dt;

		// Never into the glass or a rock, whatever the steering did: back into the water, a few passes for corners.
		for ( var k = 0; k < 3; k++ )
		{
			var push = Push( swimmer.Position, swimmer.Kind );
			if ( push.LengthSquared < 0.0001f )
				break;
			swimmer.Position += push;
		}

		// Wedged where two limits push it opposite ways (between the tunnel's tube and the surface, say): stay put
		// rather than be shoved in, and let the steering find another way.
		if ( Push( swimmer.Position, swimmer.Kind ).Length > Math.Max( before, 0.5f ) )
		{
			swimmer.Position = from;
			swimmer.Blocked += dt;
		}
	}

	private bool IsFree( Vector3 point, Kind kind ) => Push( point, kind ).LengthSquared < 0.01f;

	/// <summary>A point in open water, with a little room to spare. From a swimmer, one it can swim straight to: anywhere
	/// in the tank first, then near it, for one in a pocket between rocks.</summary>
	private bool TryPickPoint( Kind kind, out Vector3 point, Vector3? from = null )
	{
		var half = Size * 0.5f;
		var roomy = kind with { Reach = kind.Reach + Math.Min( 12f, kind.Reach ), ReachUp = kind.ReachUp + Math.Min( 8f, kind.ReachUp ) };
		for ( var k = 0; k < 60; k++ )
		{
			if ( from is { } start && k >= 40 )
			{
				var r = kind.Reach * 3f + 60f;
				point = start + new Vector3( _random.Float( -r, r ), _random.Float( -r, r ), _random.Float( -r, r ) * 0.5f );
			}
			else if ( k < 40 )
				point = new Vector3( _random.Float( -half.x, half.x ), _random.Float( -half.y, half.y ), _random.Float( -half.z, half.z ) );
			else
				break;

			if ( IsFree( point, roomy ) && ( from is not { } origin || IsClear( origin, point, kind ) ) )
				return true;
		}

		point = default;
		return false;
	}

	private bool IsClear( Vector3 from, Vector3 to, Kind kind )
	{
		var steps = (int)( from.Distance( to ) / Math.Max( kind.Reach, 10f ) ) + 1;
		for ( var k = 1; k < steps; k++ )
		{
			if ( !IsFree( Vector3.Lerp( from, to, k / (float)steps ), kind ) )
				return false;
		}
		return true;
	}

	/// <summary>How far a body at this point has to move to be clear of everything by its reach (zero when it is).</summary>
	private Vector3 Push( Vector3 p, Kind kind )
	{
		var push = Vector3.Zero;
		var half = Size * 0.5f;
		var reach = kind.Reach;
		var up = kind.ReachUp;

		// The water's own shape
		if ( Shape == TankShape.Cylinder )
		{
			var r = half.x - reach;
			var flat = new Vector2( p.x, p.y );
			var length = flat.Length;
			if ( length > r && length > 0.001f )
			{
				var back = flat / length * ( r - length );
				push += new Vector3( back.x, back.y, 0 );
			}
		}
		else
		{
			push.x += Excess( p.x, half.x - reach );
			push.y += Excess( p.y, half.y - reach );
		}
		push.z += Excess( p.z, half.z - up );

		// The glass tube through it
		if ( HoleRadius > 0f )
		{
			var d = new Vector2( p.y - HoleCentre.y, p.z - HoleCentre.z );
			var need = HoleRadius + reach;
			var length = d.Length;
			if ( length < need )
			{
				var dir = length > 0.001f ? d / length : new Vector2( 0, 1 );
				push += new Vector3( 0, dir.x, dir.y ) * ( need - length );
			}
		}

		// Rocks, coral and kelp: a cone from its foot to its top, and a margin over its top
		foreach ( var (foot, radius, height, taper) in _obstacles )
		{
			if ( p.z < foot.z - up || p.z > foot.z + height + up )
				continue;
			var t = Math.Clamp( ( p.z - foot.z ) / Math.Max( height, 1f ), 0f, 1f );
			var need = radius * ( 1f - taper * t ) + reach;
			var d = new Vector2( p.x - foot.x, p.y - foot.y );
			var length = d.Length;
			if ( length >= need )
				continue;

			// Out sideways, or over the top when that's nearer
			var over = foot.z + height + up - p.z;
			var side = need - length;
			if ( over < side )
				push.z += over;
			else
			{
				var dir = length > 0.001f ? d / length : new Vector2( 1, 0 );
				push += new Vector3( dir.x, dir.y, 0 ) * side;
			}
		}

		return push;
	}

	private static float Excess( float value, float limit )
	{
		if ( limit <= 0f )
			return -value;
		if ( value > limit )
			return limit - value;
		if ( value < -limit )
			return -limit - value;
		return 0f;
	}
}
