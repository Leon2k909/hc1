namespace Facepunch;

/// <summary>
/// The animals in one of a map's aquarium tanks, swimming about on every machine (they're scenery, so nothing is
/// networked). Each <see cref="Groups"/> entry is one species: how many, how they live together (alone, in pairs, a loose
/// shoal or a tight school), how fast and how sharply they swim, at what depth, near the rocks or in open water, and
/// how often they stop to hover. Tools/reefhall_map.py writes them from Tools/reefhall_fauna.py's SPECIES table.
///
/// Nothing ever goes into the glass, a wall, the sand, a rock, coral or kelp: every body keeps its reach (the furthest
/// its nose, fins or wingtips get from its middle, swinging and banking) clear of the water's shape less the
/// <see cref="Obstacles"/>, and a move that would end inside is pushed back out. Steering keeps them well off it before
/// that: they feel ahead and turn away early and gently, the way a fish does along the glass.
///
/// They turn by easing their rate of turn, so they curve rather than snap, and big animals take longer to settle into a
/// turn than small ones. A group follows an invisible leader: its fish keep loose places round it and swim its way, so a
/// school turns together. Fish keep a little apart, the smaller giving way. Their bodies swim in their material
/// (shaders/hc1_fish.shader), driven from here: the tail beats faster as they speed up or turn, and the pectorals
/// scull while they hover.
///
/// Everything here is in the object's own space: the tank's middle at its origin, its floor and water surface at
/// -Size.z / 2 and +Size.z / 2. They swim in the editor too, so a tank can be judged while the map is worked on.
/// `hc1_fauna_check [seconds]` runs every tank that long at once and reports what went wrong.
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

	/// <summary>The water's size, from just over the sand to just under the surface.</summary>
	[Property] public Vector3 Size { get; set; } = new( 200, 200, 200 );

	/// <summary>A glass tube running through the water along the local X axis (the Tunnel Hall's vault): no water
	/// within this of the line through <see cref="HoleCentre"/>. 0: none.</summary>
	[Property] public float HoleRadius { get; set; }

	[Property] public Vector3 HoleCentre { get; set; }

	/// <summary>Rocks, coral and kelp, "x y z radius height taper" each, separated by ';': a cone standing on x y z,
	/// this wide at its foot and narrowing by taper (a share of it) to its top. A negative taper widens it, as kelp
	/// fans out from its root.</summary>
	[Property, Hide] public string Obstacles { get; set; }

	/// <summary>One species each, as "key=value" pairs separated by spaces (see <see cref="Species"/>).</summary>
	[Property] public List<string> Groups { get; set; } = [];

	[Property] public int Seed { get; set; }

	/// <summary>Beyond this from the camera nothing small is drawn, and nothing moves more than 4 times a second.</summary>
	[Property] public float FarDistance { get; set; } = 3000f;

	/// <summary>A species, as a group entry gives it. Lengths are in inches (the models are life size).</summary>
	private sealed class Species
	{
		public string Model;
		public int Count = 1;
		// solo, pair, shoal or school
		public string Group = "solo";
		// The model's reach sideways and up and down, its length and the scales of the smallest and largest one
		public float Reach = 4f, Up = 3f, Length = 6f, ScaleMin = 1f, ScaleMax = 1f;
		// Cruising speed (inches a second), fastest turn (degrees a second), seconds to settle into a turn
		public float Speed = 5f, Turn = 90f, Response = 0.5f;
		// The steepest climb (the sine of its pitch), the roll into a full-rate turn
		public float Climb = 0.35f, Bank = 8f;
		// Depth: shares of the water's height over the sand, and no higher than Above over it (0: no limit)
		public float Low, High = 1f, Above;
		// The share of its destinations beside rock or coral; it keeps within Home of one spot (0: anywhere)
		public float Rocks, Home;
		// The chance it stops to hover at a destination, for PauseMin to PauseMax seconds
		public float Pause, PauseMin = 1f, PauseMax = 3f;
		// Room per fish in a group, in body lengths
		public float Spread = 1.5f;
		// Tail beats and pectoral strokes a second at cruising speed
		public float Beat = 2f, Fin = 2f;
		public bool Ray;

		public static Species Parse( string text )
		{
			var species = new Species();
			foreach ( var pair in text.Split( ' ', StringSplitOptions.RemoveEmptyEntries ) )
			{
				var equals = pair.IndexOf( '=' );
				if ( equals <= 0 )
					continue;
				var key = pair[..equals].ToLowerInvariant();
				var value = pair[( equals + 1 )..];
				float Number() => float.Parse( value, System.Globalization.CultureInfo.InvariantCulture );
				switch ( key )
				{
					case "model": species.Model = value; break;
					case "count": species.Count = (int)Number(); break;
					case "group": species.Group = value.ToLowerInvariant(); break;
					case "reach": species.Reach = Number(); break;
					case "up": species.Up = Number(); break;
					case "length": species.Length = Number(); break;
					case "scalemin": species.ScaleMin = Number(); break;
					case "scalemax": species.ScaleMax = Number(); break;
					case "speed": species.Speed = Number(); break;
					case "turn": species.Turn = Number(); break;
					case "response": species.Response = Number(); break;
					case "climb": species.Climb = Number(); break;
					case "bank": species.Bank = Number(); break;
					case "low": species.Low = Number(); break;
					case "high": species.High = Number(); break;
					case "above": species.Above = Number(); break;
					case "rocks": species.Rocks = Number(); break;
					case "home": species.Home = Number(); break;
					case "pause": species.Pause = Number(); break;
					case "pausemin": species.PauseMin = Number(); break;
					case "pausemax": species.PauseMax = Number(); break;
					case "spread": species.Spread = Number(); break;
					case "beat": species.Beat = Number(); break;
					case "fin": species.Fin = Number(); break;
					case "ray": species.Ray = Number() > 0.5f; break;
				}
			}
			return species;
		}
	}

	private sealed class Swimmer
	{
		public Species Species;
		public SceneObject Body;

		// Its own figures: the species' scaled by its size (a group's leader has the group's)
		public float Reach, Up, Length, Cruise, TurnRate, Response, Climb, Bank;
		// How far off the walls and the rocks its steering starts to turn it away, and how close to a rock it goes
		public float SoftWall, SoftRock, Gap;
		public float Scale = 1f;

		public Vector3 Position;
		public float Yaw, Pitch, YawRate, PitchRate, Roll, Speed;

		public Vector3 Goal;
		public float GoalUntil, Pace = 1f, Blocked;
		public float HoverUntil, HoverYaw;
		public Vector3 Home;
		public bool HasHome;

		// A group's fish: its group and its place in it; the group's leader has Members
		public Swimmer Leader;
		public List<Swimmer> Members;
		public Vector3 Slot;
		public float Wobble;

		public float SwimPhase, FinPhase, SwimAmount = 0.5f, FinAmount = 0.5f;

		// For hc1_fauna_check
		public Vector3 WatchPosition;
		public float WatchTime, Hovered, Path;

		public bool IsHovering( float time ) => time < HoverUntil;

		public Vector3 Forward
		{
			get
			{
				var yaw = Yaw.DegreeToRadian();
				var pitch = Pitch.DegreeToRadian();
				var flat = MathF.Cos( pitch );
				return new Vector3( MathF.Cos( yaw ) * flat, MathF.Sin( yaw ) * flat, MathF.Sin( pitch ) );
			}
		}
	}

	private readonly List<Swimmer> _swimmers = [];
	private readonly List<Swimmer> _bodies = [];
	private readonly List<(Vector3 Foot, float Radius, float Height, float Taper)> _obstacles = [];
	private Random _random;
	private float _time;
	private float _farStep;

	// The obstacles near each cell of a grid over the tank's plan, so a point only checks those it could touch
	private List<int>[] _grid;
	private int _gridX, _gridY;
	private float _gridCell;
	private Vector2 _gridOrigin;

	protected override void OnEnabled()
	{
		if ( Application.IsDedicatedServer )
			return;

		_random = new Random( Seed );
		_time = 0f;
		ParseObstacles();

		var species = ( Groups ?? [] ).Where( x => !string.IsNullOrWhiteSpace( x ) ).Select( Species.Parse ).ToList();
		BuildGrid( species.Count == 0 ? 10f : species.Max( x => ( x.Reach + Math.Clamp( x.Length * 0.8f, 2f, 40f ) ) * x.ScaleMax ) );

		foreach ( var kind in species )
		{
			if ( string.IsNullOrEmpty( kind.Model ) || kind.Count <= 0 )
				continue;
			var model = Model.Load( kind.Model );
			if ( model is null || model.IsError )
				continue;

			if ( kind.Group == "solo" || kind.Count == 1 )
			{
				for ( var k = 0; k < kind.Count; k++ )
					SpawnFish( kind, model, null, null );
			}
			else
				SpawnGroup( kind, model );
		}
	}

	protected override void OnDisabled()
	{
		foreach ( var swimmer in _swimmers )
			swimmer.Body?.Delete();
		_swimmers.Clear();
		_bodies.Clear();
		_obstacles.Clear();
		_grid = null;
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

	private void BuildGrid( float reach )
	{
		var half = new Vector2( Size.x, Size.y ) * 0.5f;
		_gridCell = Math.Clamp( Math.Min( Size.x, Size.y ) / 12f, 12f, 64f );
		_gridOrigin = -half;
		_gridX = Math.Max( 1, (int)MathF.Ceiling( Size.x / _gridCell ) );
		_gridY = Math.Max( 1, (int)MathF.Ceiling( Size.y / _gridCell ) );
		_grid = new List<int>[_gridX * _gridY];
		for ( var k = 0; k < _grid.Length; k++ )
			_grid[k] = [];

		for ( var index = 0; index < _obstacles.Count; index++ )
		{
			var (foot, radius, _, taper) = _obstacles[index];
			// The widest it gets (at its foot, or its top if it widens), the reach of anything near it and the cell's
			// own half-diagonal
			var widest = radius * Math.Max( 1f, 1f - taper ) + reach + _gridCell * 0.71f;
			for ( var y = 0; y < _gridY; y++ )
			{
				for ( var x = 0; x < _gridX; x++ )
				{
					var centre = _gridOrigin + new Vector2( ( x + 0.5f ) * _gridCell, ( y + 0.5f ) * _gridCell );
					if ( ( centre - new Vector2( foot.x, foot.y ) ).Length <= widest )
						_grid[y * _gridX + x].Add( index );
				}
			}
		}
	}

	private List<int> CellAt( Vector3 p )
	{
		var x = Math.Clamp( (int)( ( p.x - _gridOrigin.x ) / _gridCell ), 0, _gridX - 1 );
		var y = Math.Clamp( (int)( ( p.y - _gridOrigin.y ) / _gridCell ), 0, _gridY - 1 );
		return _grid[y * _gridX + x];
	}

	// ---------------------------------------------------------------------------------------------------------------
	// Spawning

	private Swimmer NewSwimmer( Species kind, float scale )
	{
		var swimmer = new Swimmer
		{
			Species = kind,
			Scale = scale,
			Reach = kind.Reach * scale,
			Up = kind.Up * scale,
			Length = kind.Length * scale,
			// A bigger one of a kind swims a little faster, as fish cruise at about a body length a second
			Cruise = kind.Speed * MathF.Sqrt( scale ) * _random.Float( 0.9f, 1.1f ),
			TurnRate = kind.Turn,
			Response = kind.Response,
			Climb = kind.Climb,
			Bank = kind.Bank,
			Wobble = _random.Float( 0f, 100f ),
			SwimPhase = _random.Float( 0f, MathF.PI * 2f ),
			FinPhase = _random.Float( 0f, MathF.PI * 2f ),
		};
		swimmer.Gap = Math.Clamp( 0.5f + 0.35f * swimmer.Length, 0.5f, 12f );
		swimmer.SoftWall = Math.Clamp( swimmer.Length * 0.8f, 2f, 40f );
		swimmer.SoftRock = swimmer.Gap * 0.6f;
		swimmer.Yaw = _random.Float( -180f, 180f );
		swimmer.Speed = swimmer.Cruise * 0.5f;
		return swimmer;
	}

	private Swimmer SpawnFish( Species kind, Model model, Swimmer leader, Vector3? near )
	{
		var swimmer = NewSwimmer( kind, _random.Float( kind.ScaleMin, kind.ScaleMax ) );

		if ( near is { } point && IsFree( point, swimmer.Reach, swimmer.Up, swimmer.Reach ) )
			swimmer.Position = point;
		else if ( near is { } around && TryPointNear( swimmer, around, swimmer.Length * 4f + 20f, out var close ) )
			swimmer.Position = close;
		else if ( leader is not null && TryPointNear( swimmer, leader.Position, leader.Reach * 2f + 40f, out var byLeader ) )
			swimmer.Position = byLeader;
		else
		{
			if ( kind.Home > 0f && leader is null && TryRockPoint( swimmer, null, out var home ) )
			{
				swimmer.Home = home;
				swimmer.HasHome = true;
			}
			if ( !TryPickGoal( swimmer, out var start, false ) )
				return null;
			swimmer.Position = start;
		}

		if ( leader is null && kind.Home > 0f && !swimmer.HasHome )
		{
			swimmer.Home = swimmer.Position;
			swimmer.HasHome = true;
		}

		swimmer.Goal = swimmer.Position;
		swimmer.Leader = leader;
		swimmer.WatchPosition = swimmer.Position;

		swimmer.Body = new SceneObject( Scene.SceneWorld, model, Transform.World );
		swimmer.Body.Flags.CastShadows = false;
		swimmer.Body.Attributes.Set( "SwimDriven", 1f );

		_swimmers.Add( swimmer );
		_bodies.Add( swimmer );
		return swimmer;
	}

	/// <summary>A pair, shoal or school: an invisible leader with room round it for the group, and the fish in loose
	/// places round it.</summary>
	private void SpawnGroup( Species kind, Model model )
	{
		var pair = kind.Group == "pair";
		var school = kind.Group == "school";
		var spacing = kind.Length * kind.ScaleMax * Math.Max( kind.Spread, 0.6f );
		var radius = pair ? spacing * 0.5f : spacing * 0.75f * MathF.Cbrt( kind.Count );

		var leader = NewSwimmer( kind, 1f );
		leader.Cruise = kind.Speed;
		leader.Reach = kind.Reach * kind.ScaleMax + radius * 0.7f;
		leader.Up = kind.Up * kind.ScaleMax + radius * 0.35f;
		leader.Length = kind.Length;
		// A group turns more slowly than any one of its fish, so its fish can keep up round the outside of a turn
		leader.TurnRate = kind.Turn * ( school ? 0.45f : 0.55f );
		leader.Response = kind.Response * 1.6f;
		leader.SoftWall = Math.Clamp( kind.Length * 1.5f + radius * 0.3f, 3f, 40f );
		leader.SoftRock = leader.Gap * 0.6f;
		leader.Members = [];

		if ( kind.Home > 0f && TryRockPoint( leader, null, out var home ) )
		{
			leader.Home = home;
			leader.HasHome = true;
		}
		if ( !TryPickGoal( leader, out var start, false ) )
		{
			// No room for the group as one: they live as single fish instead
			for ( var k = 0; k < kind.Count; k++ )
				SpawnFish( kind, model, null, null );
			return;
		}
		leader.Position = start;
		leader.Goal = start;
		if ( kind.Home > 0f && !leader.HasHome )
		{
			leader.Home = start;
			leader.HasHome = true;
		}
		_swimmers.Add( leader );

		var frame = Rotation.FromYaw( leader.Yaw );
		var slots = new List<Vector3>();
		for ( var k = 0; k < kind.Count; k++ )
		{
			Vector3 slot;
			if ( pair )
				slot = new Vector3( k == 0 ? spacing * 0.25f : -spacing * 0.25f, k == 0 ? spacing * 0.45f : -spacing * 0.45f, k == 0 ? 0.2f : -0.2f ) * 1f;
			else
			{
				// Spread through a flattened ball, the school longer than it is deep, as real ones are, each place
				// keeping its distance from the others (the furthest of a few tries where it can't)
				slot = default;
				var best = -1f;
				for ( var tries = 0; tries < 30; tries++ )
				{
					var direction = new Vector3( _random.Float( -1f, 1f ), _random.Float( -1f, 1f ), _random.Float( -1f, 1f ) );
					if ( direction.LengthSquared > 1f || direction.LengthSquared < 0.01f )
						direction = direction.Normal * _random.Float( 0.2f, 1f );
					var candidate = new Vector3( direction.x * 1.2f, direction.y, direction.z * ( school ? 0.45f : 0.6f ) ) * radius;
					var nearest = slots.Count == 0 ? float.MaxValue : slots.Min( x => x.Distance( candidate ) );
					if ( nearest > best )
					{
						best = nearest;
						slot = candidate;
					}
					if ( nearest >= spacing * 0.9f )
						break;
				}
			}
			slots.Add( slot );

			var fish = SpawnFish( kind, model, leader, leader.Position + frame * slot );
			if ( fish is null )
				continue;
			fish.Slot = slot;
			fish.Yaw = leader.Yaw + _random.Float( -20f, 20f );
			leader.Members.Add( fish );
		}
	}

	// ---------------------------------------------------------------------------------------------------------------
	// Each frame

	protected override void OnUpdate()
	{
		if ( _bodies.Count == 0 )
			return;

		var dt = Math.Min( Time.Delta, 0.1f );
		// In the editor the view is the editor's own camera, which the scene can't see (its Scene.Camera is whatever
		// camera the map holds, like the minimap's capture camera high above it), so there every fish is drawn
		var camera = Scene.IsEditor ? null : Scene.Camera;
		var world = WorldTransform;
		var extent = Math.Max( Size.x, Size.y );
		var cameraLocal = camera.IsValid() ? world.PointToLocal( camera.WorldPosition ) : Vector3.Zero;
		var far = camera.IsValid() && cameraLocal.Length > FarDistance + extent;

		// Far away, it all moves a few times a second, and the small fish aren't drawn.
		if ( far )
		{
			_farStep += dt;
			if ( _farStep < 0.25f )
				return;
			dt = Math.Min( _farStep, 0.5f );
			_farStep = 0f;
		}

		Step( dt );

		foreach ( var swimmer in _bodies )
		{
			var big = swimmer.Reach > 20f;
			var near = !camera.IsValid() || ( swimmer.Position - cameraLocal ).Length < CullDistance( swimmer );
			swimmer.Body.RenderingEnabled = big || ( !far && near );
			if ( swimmer.Body.RenderingEnabled )
				Place( swimmer, world );
		}
	}

	// A small fish further off than this isn't drawn: past it, it's a few pixels behind the glass.
	private float CullDistance( Swimmer swimmer ) => Math.Clamp( swimmer.Length * 260f, 800f, FarDistance );

	private void Place( Swimmer swimmer, Transform world )
	{
		var rotation = Rotation.LookAt( swimmer.Forward, Vector3.Up ) * Rotation.FromRoll( swimmer.Roll );
		swimmer.Body.Transform = new Transform( world.PointToWorld( swimmer.Position ), world.Rotation * rotation, swimmer.Scale );
		swimmer.Body.Attributes.Set( "SwimPhase", swimmer.SwimPhase );
		swimmer.Body.Attributes.Set( "SwimAmount", swimmer.SwimAmount );
		swimmer.Body.Attributes.Set( "FinPhase", swimmer.FinPhase );
		swimmer.Body.Attributes.Set( "FinAmount", swimmer.FinAmount );
	}

	private void Step( float dt )
	{
		_time += dt;

		// Leaders and lone fish first, so the groups follow where their leaders are now.
		foreach ( var swimmer in _swimmers )
		{
			if ( swimmer.Leader is null )
				Wander( swimmer, dt );
		}

		foreach ( var swimmer in _swimmers )
		{
			if ( swimmer.Leader is not null )
				Follow( swimmer, dt );
		}

		Separate();
		Separate();

		foreach ( var swimmer in _bodies )
			Animate( swimmer, dt );
	}

	/// <summary>A lone fish, or a group's leader: swims to a spot, maybe hovers there a while, then picks another.</summary>
	private void Wander( Swimmer swimmer, float dt )
	{
		var kind = swimmer.Species;
		var toGoal = swimmer.Goal - swimmer.Position;
		var arrive = Math.Max( swimmer.Length * 0.6f, 1.5f ) + swimmer.Cruise * 0.4f + ( swimmer.Members is null ? 0f : swimmer.Reach * 0.3f );

		if ( swimmer.IsHovering( _time ) )
		{
			// Hovering: barely moving, turning slowly to look about, the pectorals doing the work.
			var look = Rotation.FromYaw( swimmer.HoverYaw ).Forward;
			var drift = Avoid( swimmer, look * 0.4f );
			Steer( swimmer, drift, dt, 0.35f );
			Pace( swimmer, swimmer.Cruise * 0.04f, dt );
			Move( swimmer, dt );
			swimmer.Hovered += dt;
			if ( _random.NextSingle() < dt * 0.15f )
				swimmer.HoverYaw = swimmer.Yaw + _random.Float( -70f, 70f );
			return;
		}

		if ( toGoal.Length < arrive || _time >= swimmer.GoalUntil || swimmer.Blocked > 2.5f )
		{
			var arrived = toGoal.Length < arrive;
			if ( arrived && kind.Pause > 0f && _random.NextSingle() < kind.Pause )
			{
				swimmer.HoverUntil = _time + _random.Float( kind.PauseMin, Math.Max( kind.PauseMin, kind.PauseMax ) );
				swimmer.HoverYaw = swimmer.Yaw + _random.Float( -60f, 60f );
			}
			if ( TryPickGoal( swimmer, out var goal, true ) )
				swimmer.Goal = goal;
			var distance = swimmer.Goal.Distance( swimmer.Position );
			swimmer.GoalUntil = _time + distance / Math.Max( swimmer.Cruise, 0.5f ) * 2.5f + _random.Float( 4f, 10f );
			swimmer.Pace = _random.Float( 0.8f, 1.15f );
			swimmer.Blocked = 0f;
			toGoal = swimmer.Goal - swimmer.Position;
			if ( swimmer.IsHovering( _time ) )
				return;
		}

		var desired = toGoal.Normal;
		var slow = 1f;

		// Keep to its depth and its home, gently.
		desired += Keep( swimmer );

		var (avoided, urgency, pace) = LookAhead( swimmer, Avoid( swimmer, desired ) );
		Steer( swimmer, avoided, dt, urgency );

		// Ease off coming up to where it's going, and when it has to turn hard.
		if ( kind.Pause > 0f )
			slow = Math.Clamp( toGoal.Length / ( swimmer.Length * 2f + swimmer.Cruise ), 0.35f, 1f );
		var turning = Math.Abs( swimmer.YawRate ) / Math.Max( swimmer.TurnRate, 1f );
		Pace( swimmer, swimmer.Cruise * swimmer.Pace * slow * pace * ( 1f - 0.35f * turning ), dt );
		Move( swimmer, dt );
	}

	/// <summary>A fish in a group: keeps its place round the leader, loosely, swimming the leader's way.</summary>
	private void Follow( Swimmer swimmer, float dt )
	{
		var leader = swimmer.Leader;
		var kind = swimmer.Species;
		var school = kind.Group == "school";
		var pair = kind.Group == "pair";

		// Its place drifts about it slowly: a school's fish hold theirs closely, a shoal's mill about.
		var looseness = school ? 0.25f : pair ? 0.5f : 0.7f;
		var spacing = kind.Length * kind.ScaleMax * Math.Max( kind.Spread, 0.6f );
		var t = _time * ( 0.12f + 0.05f * MathF.Sin( swimmer.Wobble ) );
		var drift = new Vector3( MathF.Sin( t * 1.3f + swimmer.Wobble ), MathF.Sin( t * 1.1f + swimmer.Wobble * 1.7f ),
			MathF.Sin( t * 0.9f + swimmer.Wobble * 2.3f ) * 0.4f ) * spacing * looseness;
		var frame = Rotation.FromYaw( leader.Yaw );
		var place = leader.Position + frame * ( swimmer.Slot + drift );
		var toPlace = place - swimmer.Position;
		var along = Vector3.Dot( toPlace, leader.Forward );

		Vector3 desired;
		float speed;
		if ( leader.IsHovering( _time ) )
		{
			// The group has stopped: each fish drifts to its place and hangs there, facing about as it likes.
			var hover = Rotation.FromYaw( leader.HoverYaw + MathF.Sin( swimmer.Wobble * 3f ) * 40f ).Forward;
			desired = hover * 0.5f + toPlace / Math.Max( swimmer.Length * 3f, 1f );
			speed = Math.Clamp( toPlace.Length / Math.Max( swimmer.Length * 4f, 1f ), 0.04f, 0.6f ) * swimmer.Cruise;
			swimmer.Hovered += dt;
		}
		else
		{
			var align = school ? 1f : pair ? 0.7f : 0.45f;
			desired = leader.Forward * align + toPlace / Math.Max( spacing * 1.5f, 1f );
			// Catch up when it has fallen behind, ease off when it's ahead: within half a cruise either way.
			var catchUp = Math.Clamp( along / Math.Max( spacing * 2f, 1f ), -0.5f, 0.9f );
			speed = leader.Speed * ( 1f + catchUp );
			if ( toPlace.Length > spacing * 4f )
				speed = Math.Max( speed, swimmer.Cruise * 1.6f );
		}

		var (avoided, urgency, pace) = LookAhead( swimmer, Avoid( swimmer, desired ) );
		Steer( swimmer, avoided, dt, urgency );
		Pace( swimmer, Math.Min( speed * pace, swimmer.Cruise * 2f ), dt );
		Move( swimmer, dt );
	}

	/// <summary>Its depth band, its home and (for the bottom dwellers) its height over the sand: a nudge back towards
	/// them, growing the further out it is.</summary>
	private Vector3 Keep( Swimmer swimmer )
	{
		var push = Vector3.Zero;
		var (low, high) = DepthBand( swimmer );
		var z = swimmer.Position.z;
		var band = Math.Max( high - low, 1f );
		if ( z < low )
			push.z += Math.Min( ( low - z ) / band, 1f ) * 0.6f;
		else if ( z > high )
			push.z -= Math.Min( ( z - high ) / band, 1f ) * 0.6f;

		if ( swimmer.HasHome && swimmer.Species.Home > 0f )
		{
			var away = swimmer.Position - swimmer.Home;
			var over = away.Length - swimmer.Species.Home;
			if ( over > 0f )
				push -= away.Normal * Math.Min( over / swimmer.Species.Home, 1.5f );
		}
		return push;
	}

	/// <summary>Turns a heading away from what's near: the walls, the glass and the sand within its SoftWall, rocks
	/// within its SoftRock, and other fish. Small fish give way to bigger ones and keep clear of sharks and rays.</summary>
	private Vector3 Avoid( Swimmer swimmer, Vector3 desired )
	{
		if ( desired.LengthSquared < 1e-6f )
			desired = swimmer.Forward;
		desired = desired.Normal;

		var soft = Push( swimmer.Position, swimmer.Reach + swimmer.SoftWall, swimmer.Up + swimmer.SoftWall * 0.5f,
			swimmer.Reach + swimmer.SoftRock );
		if ( soft.LengthSquared > 1e-6f )
			desired += soft / Math.Max( swimmer.SoftWall * 0.5f, 1f );

		if ( swimmer.Members is not null )
		{
			// A group's leader takes its fish out of the way of a shark or a ray, as a school parts round one
			var clear = Vector3.Zero;
			foreach ( var other in _bodies )
			{
				if ( other.Length < swimmer.Length * 3f )
					continue;
				var room = swimmer.Reach + other.Reach * 1.2f + 12f;
				var away = swimmer.Position - other.Position;
				var distance = away.Length;
				if ( distance >= room || distance < 0.001f )
					continue;
				clear += away / distance * ( 1f - distance / room ) * 2f;
			}
			desired += clear * 1.5f;
		}
		else if ( swimmer.Body is not null )
		{
			var apart = Vector3.Zero;
			foreach ( var other in _bodies )
			{
				if ( other == swimmer )
					continue;
				var bigger = other.Length > swimmer.Length * 3f;
				var room = ( swimmer.Reach + other.Reach ) * ( bigger ? 1.4f : 0.9f ) + ( bigger ? 12f : swimmer.Gap );
				var away = swimmer.Position - other.Position;
				var distance = away.Length;
				if ( distance >= room || distance < 0.001f )
					continue;
				// The smaller gives way: a fish barely moves for one a fifth its size
				var share = other.Length / ( other.Length + swimmer.Length );
				apart += away / distance * ( 1f - distance / room ) * share * 2f;
			}
			desired += apart * 1.5f;
		}

		return desired.LengthSquared < 1e-6f ? swimmer.Forward : desired.Normal;
	}

	/// <summary>Feels ahead: where it will be in a second or so, and its nose beyond that. If that isn't open water,
	/// it looks round for the way that is, nearest where it wants to go, and turns into it harder and slower.</summary>
	private (Vector3 Direction, float Urgency, float Pace) LookAhead( Swimmer swimmer, Vector3 desired )
	{
		var look = swimmer.Speed * 1.2f + swimmer.Length * 0.6f + 1f;
		if ( IsFree( swimmer.Position + swimmer.Forward * look, swimmer.Reach, swimmer.Up, swimmer.Reach )
			&& IsFree( swimmer.Position + desired * look, swimmer.Reach, swimmer.Up, swimmer.Reach ) )
			return (desired, 1f, 1f);

		var best = desired;
		var bestScore = float.MinValue;
		var forward = swimmer.Forward;
		foreach ( var (yaw, pitch) in Fan )
		{
			var climb = pitch * swimmer.Climb;
			var flat = MathF.Sqrt( 1f - climb * climb );
			var direction = new Vector3( yaw.x * flat, yaw.y * flat, climb );
			var score = Vector3.Dot( direction, desired ) + 0.6f * Vector3.Dot( direction, forward );
			if ( score > bestScore && IsFree( swimmer.Position + direction * look, swimmer.Reach, swimmer.Up, swimmer.Reach ) )
			{
				best = direction;
				bestScore = score;
			}
		}
		if ( bestScore == float.MinValue )
			swimmer.Blocked += 0.05f;
		return (best, 1.6f, 0.6f);
	}

	// The ways a swimmer looks round in when the water ahead is blocked: every 15 degrees round, level, a little up and
	// down and more (shares of its climb).
	private static readonly (Vector2 Yaw, float Pitch)[] Fan = Enumerable.Range( 0, 24 )
		.SelectMany( k => new[] { 0f, 0.5f, -0.5f, 1f, -1f }.Select( pitch =>
			(new Vector2( MathF.Cos( k * 15f * MathF.PI / 180f ), MathF.Sin( k * 15f * MathF.PI / 180f ) ), pitch) ) )
		.ToArray();

	/// <summary>Turns towards a heading by easing its rate of turn: it builds up into a turn over its Response and
	/// eases out of it as it comes round, so it curves. It banks into the turn, and climbs no steeper than it can.</summary>
	private static void Steer( Swimmer swimmer, Vector3 desired, float dt, float urgency )
	{
		if ( desired.LengthSquared < 1e-6f )
			return;
		desired = desired.Normal;

		var response = Math.Max( swimmer.Response, 0.08f );
		var ease = Math.Min( 1f, dt / ( response * 0.5f ) );
		var turn = swimmer.TurnRate * urgency;

		if ( desired.WithZ( 0 ).LengthSquared > 1e-4f )
		{
			var targetYaw = MathF.Atan2( desired.y, desired.x ).RadianToDegree();
			var wantYaw = Math.Clamp( DeltaAngle( swimmer.Yaw, targetYaw ) / response, -turn, turn );
			swimmer.YawRate += ( wantYaw - swimmer.YawRate ) * ease;
		}
		else
			swimmer.YawRate -= swimmer.YawRate * ease;
		swimmer.Yaw = Wrap( swimmer.Yaw + swimmer.YawRate * dt );

		var maxPitch = MathF.Asin( Math.Clamp( swimmer.Climb, 0f, 0.95f ) ).RadianToDegree();
		var targetPitch = Math.Clamp( MathF.Asin( Math.Clamp( desired.z, -1f, 1f ) ).RadianToDegree(), -maxPitch, maxPitch );
		var wantPitch = Math.Clamp( ( targetPitch - swimmer.Pitch ) / response, -turn * 0.6f, turn * 0.6f );
		swimmer.PitchRate += ( wantPitch - swimmer.PitchRate ) * ease;
		swimmer.Pitch = Math.Clamp( swimmer.Pitch + swimmer.PitchRate * dt, -maxPitch, maxPitch );

		// Bank into the turn, as a ray or a shark does; ease out of it on the straight.
		var bank = Math.Clamp( -swimmer.YawRate / Math.Max( swimmer.TurnRate, 1f ), -1f, 1f ) * swimmer.Bank;
		swimmer.Roll += ( bank - swimmer.Roll ) * Math.Min( 1f, dt / response );
	}

	private static void Pace( Swimmer swimmer, float target, float dt )
	{
		// Speeding up and slowing down take about twice as long as settling into a turn: water is heavy.
		var ease = Math.Min( 1f, dt / Math.Max( swimmer.Response * 2f, 0.2f ) );
		swimmer.Speed += ( Math.Max( target, 0f ) - swimmer.Speed ) * ease;
	}

	private void Move( Swimmer swimmer, float dt )
	{
		var from = swimmer.Position;
		var before = Push( from, swimmer.Reach, swimmer.Up, swimmer.Reach ).Length;
		swimmer.Position += swimmer.Forward * swimmer.Speed * dt;

		// Never into the glass or a rock, whatever the steering did: back into the water, a few passes for corners.
		for ( var k = 0; k < 3; k++ )
		{
			var push = Push( swimmer.Position, swimmer.Reach, swimmer.Up, swimmer.Reach );
			if ( push.LengthSquared < 0.0001f )
				break;
			swimmer.Position += push;
		}

		// Wedged where two limits push it opposite ways (between the tunnel's tube and the surface, say): stay put
		// rather than be shoved in, and let the steering find another way.
		if ( Push( swimmer.Position, swimmer.Reach, swimmer.Up, swimmer.Reach ).Length > Math.Max( before, 0.05f ) )
		{
			swimmer.Position = from;
			swimmer.Blocked += dt;
		}
	}

	/// <summary>Where a body runs from nose to tail, and how far it reaches out from that line: its half-thickness
	/// sideways and its half-height up and down (a ray's wings the other way round). The models' noses sit about
	/// 0.45 of a length ahead of their origins.</summary>
	private static (Vector3 Nose, Vector3 Tail, float Side, float High) BodyLine( Swimmer swimmer )
	{
		var forward = swimmer.Forward;
		var nose = swimmer.Position + forward * ( swimmer.Length * 0.45f );
		var tail = nose - forward * swimmer.Length;
		return swimmer.Species.Ray
			? (nose, tail, swimmer.Reach * 0.8f, swimmer.Up * 0.3f)
			: (nose, tail, swimmer.Length * 0.1f, swimmer.Up * 0.85f);
	}

	/// <summary>How far two bodies overlap (0 when they don't), and the way that parts them, from b towards a.</summary>
	private static float Overlap( Swimmer a, Swimmer b, out Vector3 apart )
	{
		apart = Vector3.Zero;
		var reach = ( a.Length + b.Length ) * 0.5f + a.Up + b.Up + ( a.Species.Ray || b.Species.Ray ? a.Reach + b.Reach : 0f );
		if ( ( a.Position - b.Position ).LengthSquared > reach * reach )
			return 0f;

		var lineA = BodyLine( a );
		var lineB = BodyLine( b );
		ClosestPoints( lineA.Nose, lineA.Tail, lineB.Nose, lineB.Tail, out var onA, out var onB );
		var between = onA - onB;
		var distance = between.Length;
		var direction = distance > 0.001f ? between / distance : ( a.Position - b.Position ).Normal;
		var up = Math.Abs( direction.z );
		var need = MathX.Lerp( lineA.Side, lineA.High, up ) + MathX.Lerp( lineB.Side, lineB.High, up ) + 0.15f;
		if ( distance >= need )
			return 0f;
		apart = direction;
		return need - distance;
	}

	/// <summary>The closest points of two segments.</summary>
	private static void ClosestPoints( Vector3 p1, Vector3 q1, Vector3 p2, Vector3 q2, out Vector3 c1, out Vector3 c2 )
	{
		var d1 = q1 - p1;
		var d2 = q2 - p2;
		var r = p1 - p2;
		var a = Vector3.Dot( d1, d1 );
		var e = Vector3.Dot( d2, d2 );
		var f = Vector3.Dot( d2, r );
		float s, t;
		if ( a < 1e-6f && e < 1e-6f )
		{
			c1 = p1;
			c2 = p2;
			return;
		}
		if ( a < 1e-6f )
		{
			s = 0f;
			t = Math.Clamp( f / e, 0f, 1f );
		}
		else
		{
			var c = Vector3.Dot( d1, r );
			if ( e < 1e-6f )
			{
				t = 0f;
				s = Math.Clamp( -c / a, 0f, 1f );
			}
			else
			{
				var b = Vector3.Dot( d1, d2 );
				var denom = a * e - b * b;
				s = denom > 1e-6f ? Math.Clamp( ( b * f - c * e ) / denom, 0f, 1f ) : 0f;
				t = ( b * s + f ) / e;
				if ( t < 0f )
				{
					t = 0f;
					s = Math.Clamp( -c / a, 0f, 1f );
				}
				else if ( t > 1f )
				{
					t = 1f;
					s = Math.Clamp( ( b - c ) / a, 0f, 1f );
				}
			}
		}
		c1 = p1 + d1 * s;
		c2 = p2 + d2 * t;
	}

	/// <summary>No fish ever swims through another: where the steering hasn't kept two apart, they're moved apart
	/// along the line between their bodies, the smaller one most, and never into the glass or a rock.</summary>
	private void Separate()
	{
		for ( var i = 0; i < _bodies.Count; i++ )
		{
			var a = _bodies[i];
			for ( var j = i + 1; j < _bodies.Count; j++ )
			{
				var b = _bodies[j];
				var overlap = Overlap( a, b, out var apart );
				if ( overlap <= 0f )
					continue;
				var shareA = b.Length / ( a.Length + b.Length );
				Nudge( a, apart * ( overlap * shareA ) );
				Nudge( b, -apart * ( overlap * ( 1f - shareA ) ) );
			}
		}
	}

	private void Nudge( Swimmer swimmer, Vector3 by )
	{
		var moved = swimmer.Position + by;
		var push = Push( moved, swimmer.Reach, swimmer.Up, swimmer.Reach );
		if ( push.LengthSquared < 0.0001f )
			swimmer.Position = moved;
		else if ( Push( moved + push, swimmer.Reach, swimmer.Up, swimmer.Reach ).LengthSquared < 0.0001f )
			swimmer.Position = moved + push;
	}

	/// <summary>The shader's swimming: the tail beats faster and harder as it speeds up or turns, and barely at all
	/// while it hovers, when the pectorals scull instead. A ray's wings beat slower and steadier.</summary>
	private static void Animate( Swimmer swimmer, float dt )
	{
		var kind = swimmer.Species;
		var ratio = swimmer.Speed / Math.Max( swimmer.Cruise, 0.1f );
		var turning = Math.Min( Math.Abs( swimmer.YawRate ) / Math.Max( swimmer.TurnRate, 1f ), 1f );

		float amount, beats;
		if ( kind.Ray )
		{
			amount = 0.55f + 0.45f * Math.Min( ratio, 1.4f );
			beats = kind.Beat * ( 0.7f + 0.3f * Math.Min( ratio, 1.5f ) );
		}
		else
		{
			amount = Math.Clamp( 0.18f + 0.8f * ratio + 0.45f * turning, 0.15f, 1.3f );
			beats = kind.Beat * Math.Clamp( 0.35f + 0.65f * ratio + 0.4f * turning, 0.3f, 1.8f );
		}
		var ease = Math.Min( 1f, dt * 3f );
		swimmer.SwimAmount += ( amount - swimmer.SwimAmount ) * ease;
		swimmer.SwimPhase = ( swimmer.SwimPhase + MathF.PI * 2f * beats * dt ) % ( MathF.PI * 2f );

		// Pectorals: folded in at speed, sculling while slow or hovering
		var fin = Math.Clamp( 1.1f - 0.75f * ratio, 0.2f, 1f );
		swimmer.FinAmount += ( fin - swimmer.FinAmount ) * ease;
		swimmer.FinPhase = ( swimmer.FinPhase + MathF.PI * 2f * kind.Fin * ( 0.6f + 0.5f * swimmer.FinAmount ) * dt ) % ( MathF.PI * 2f );
	}

	// ---------------------------------------------------------------------------------------------------------------
	// Places to swim to

	/// <summary>Its depth band in the tank's space, kept inside where its body fits.</summary>
	private (float Low, float High) DepthBand( Swimmer swimmer )
	{
		var kind = swimmer.Species;
		var floor = -Size.z * 0.5f;
		var bottom = floor + swimmer.Up;
		var top = Size.z * 0.5f - swimmer.Up;
		var low = Math.Max( floor + kind.Low * Size.z, bottom );
		var high = Math.Min( floor + kind.High * Size.z, top );
		if ( kind.Above > 0f )
			high = Math.Min( high, floor + kind.Above );
		if ( high < low )
			high = low = Math.Clamp( high, bottom, Math.Max( bottom, top ) );
		return (low, high);
	}

	/// <summary>Somewhere to swim to: beside a rock (its Rocks share of the time) or out in its depth band, within its
	/// home's reach, in open water with room to spare, and (from where it is) in a straight line it can swim.</summary>
	private bool TryPickGoal( Swimmer swimmer, out Vector3 point, bool fromHere )
	{
		var kind = swimmer.Species;
		Vector3? from = fromHere ? swimmer.Position : null;
		if ( kind.Rocks > 0f && _obstacles.Count > 0 && _random.NextSingle() < kind.Rocks && TryRockPoint( swimmer, from, out point ) )
			return true;

		var half = Size * 0.5f;
		var (low, high) = DepthBand( swimmer );
		var roomy = swimmer.Reach + swimmer.SoftWall * 0.6f;
		var roomyUp = swimmer.Up + swimmer.SoftWall * 0.3f;
		for ( var k = 0; k < 60; k++ )
		{
			if ( swimmer.HasHome && kind.Home > 0f )
			{
				var r = kind.Home;
				point = swimmer.Home + new Vector3( _random.Float( -r, r ), _random.Float( -r, r ), _random.Float( -r, r ) * 0.5f );
				point.z = Math.Clamp( point.z, low, high );
			}
			else if ( fromHere && k >= 40 )
			{
				var r = swimmer.Reach * 3f + swimmer.Length * 4f + 30f;
				point = swimmer.Position + new Vector3( _random.Float( -r, r ), _random.Float( -r, r ), _random.Float( -r, r ) * 0.4f );
				point.z = Math.Clamp( point.z, low, high );
			}
			else
				point = new Vector3( _random.Float( -half.x, half.x ), _random.Float( -half.y, half.y ), _random.Float( low, high ) );

			// Room to spare near the walls on a first try; then just room.
			var wall = k < 30 ? roomy : swimmer.Reach;
			var wallUp = k < 30 ? roomyUp : swimmer.Up;
			if ( !IsFree( point, wall, wallUp, swimmer.Reach + swimmer.Gap * 0.5f ) )
				continue;
			if ( from is { } start && !IsClear( start, point, swimmer ) )
				continue;
			return true;
		}

		point = default;
		return false;
	}

	/// <summary>A spot beside a rock, coral or kelp, a little off it at the height of its depth band.</summary>
	private bool TryRockPoint( Swimmer swimmer, Vector3? from, out Vector3 point )
	{
		var (low, high) = DepthBand( swimmer );
		for ( var k = 0; k < 24 && _obstacles.Count > 0; k++ )
		{
			var (foot, radius, height, taper) = _obstacles[_random.Int( 0, _obstacles.Count - 1 )];
			if ( swimmer.HasHome && swimmer.Species.Home > 0f && ( new Vector2( foot.x - swimmer.Home.x, foot.y - swimmer.Home.y ) ).Length
				> swimmer.Species.Home + radius )
				continue;
			var zLow = Math.Max( low, foot.z );
			var zHigh = Math.Min( high, foot.z + height );
			if ( zHigh < zLow )
				continue;
			var z = _random.Float( zLow, zHigh );
			var t = Math.Clamp( ( z - foot.z ) / Math.Max( height, 1f ), 0f, 1f );
			var at = radius * ( 1f - taper * t ) + swimmer.Reach + swimmer.Gap;
			var angle = _random.Float( 0f, MathF.PI * 2f );
			point = new Vector3( foot.x + MathF.Cos( angle ) * at, foot.y + MathF.Sin( angle ) * at, z );
			if ( !IsFree( point, swimmer.Reach + swimmer.SoftWall * 0.3f, swimmer.Up, swimmer.Reach + swimmer.Gap * 0.5f ) )
				continue;
			if ( from is { } start && !IsClear( start, point, swimmer ) )
				continue;
			return true;
		}
		point = default;
		return false;
	}

	/// <summary>A free point near another, for a group's fish whose place is in a rock.</summary>
	private bool TryPointNear( Swimmer swimmer, Vector3 near, float radius, out Vector3 point )
	{
		for ( var k = 0; k < 40; k++ )
		{
			var r = radius * ( 0.3f + k / 40f );
			point = near + new Vector3( _random.Float( -r, r ), _random.Float( -r, r ), _random.Float( -r, r ) * 0.4f );
			if ( IsFree( point, swimmer.Reach, swimmer.Up, swimmer.Reach + swimmer.Gap * 0.3f ) )
				return true;
		}
		point = default;
		return false;
	}

	private bool IsClear( Vector3 from, Vector3 to, Swimmer swimmer )
	{
		var steps = (int)( from.Distance( to ) / Math.Max( Math.Min( swimmer.Reach, swimmer.Up ) * 1.5f, 2f ) ) + 1;
		for ( var k = 1; k < steps; k++ )
		{
			if ( !IsFree( Vector3.Lerp( from, to, k / (float)steps ), swimmer.Reach, swimmer.Up, swimmer.Reach ) )
				return false;
		}
		return true;
	}

	private bool IsFree( Vector3 point, float reach, float up, float rockReach ) => Push( point, reach, up, rockReach ).LengthSquared < 0.0004f;

	/// <summary>How far a body at this point has to move to be clear of the water's edges by reach (up and down by
	/// up), and of the rocks by rockReach: zero when it is.</summary>
	private Vector3 Push( Vector3 p, float reach, float up, float rockReach )
	{
		var push = Vector3.Zero;
		var half = Size * 0.5f;

		// The water's own shape
		if ( Shape == TankShape.Cylinder )
		{
			var r = half.x - reach;
			var flat = new Vector2( p.x, p.y );
			var length = flat.Length;
			if ( length > r && length > 0.001f )
			{
				var back = flat / length * ( Math.Max( r, 0f ) - length );
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
		if ( _grid is null )
			return push;
		foreach ( var index in CellAt( p ) )
		{
			var (foot, radius, height, taper) = _obstacles[index];
			if ( p.z < foot.z - up || p.z > foot.z + height + up )
				continue;
			var t = Math.Clamp( ( p.z - foot.z ) / Math.Max( height, 1f ), 0f, 1f );
			var need = radius * ( 1f - taper * t ) + rockReach;
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

	private static float Wrap( float degrees )
	{
		degrees %= 360f;
		if ( degrees > 180f )
			degrees -= 360f;
		else if ( degrees < -180f )
			degrees += 360f;
		return degrees;
	}

	private static float DeltaAngle( float from, float to ) => Wrap( to - from );

	// ---------------------------------------------------------------------------------------------------------------
	// Checking

	private sealed class Report
	{
		public int Fish, Steps, Outside, Wedged, Close, Still;
		public float WorstOutside, Closest;
		public double StepMs;
		public int StepCount;
		public readonly Dictionary<string, int> ClosePairs = [];
		public readonly Dictionary<string, (float Speed, float Cruise, int Count)> Speeds = [];
	}

	/// <summary>Runs every tank for this many seconds at once, and logs: any body's reach going into the glass, a wall
	/// or a rock (it never should), fish closer than half a body length to another, fish that have hardly moved in 20
	/// seconds while not hovering, and each species' mean speed against its cruise.</summary>
	[ConCmd( "hc1_fauna_check" )]
	public static void CheckCommand( float seconds = 30f )
	{
		var scene = Game.ActiveScene;
		if ( scene is null )
		{
			Log.Warning( "hc1_fauna_check: no scene" );
			return;
		}

		var report = new Report();
		var all = scene.GetAllComponents<TankFauna>().ToList();
		if ( all.Count == 0 || all.All( x => x._bodies.Count == 0 ) )
			Log.Warning( $"hc1_fauna_check: {scene.Name} has {all.Count} tanks, {all.Count( x => x.Active )} active, none with animals" );
		var tanks = all.Where( x => x.Active && x._bodies.Count > 0 ).ToList();
		foreach ( var tank in tanks )
			tank.Check( seconds, report );

		Log.Info( $"hc1_fauna_check: {tanks.Count} tanks, {report.Fish} animals, {seconds:0} s each: worst reach into glass "
			+ $"or rock {report.WorstOutside:0.000} ({report.Outside} of {report.Steps} fish-steps over 0.05), "
			+ $"{report.Close} fish-steps overlapping another by over 0.05, {report.Still} stuck for 20 s" );
		Log.Info( $"  every tank's step took {report.StepMs / Math.Max( report.StepCount, 1 ):0.000} ms (all close up, none skipped)" );
		if ( report.Close > 0 )
			Log.Info( $"  deepest overlap {report.Closest:0.00}; " + string.Join( ", ",
				report.ClosePairs.OrderByDescending( x => x.Value ).Take( 8 ).Select( x => $"{x.Key} {x.Value}" ) ) );
		foreach ( var (name, (speed, cruise, count)) in report.Speeds.OrderBy( x => x.Key ) )
			Log.Info( $"  {name}: {count}, mean speed {speed / Math.Max( count, 1 ):0.0} in/s against a cruise of {cruise / Math.Max( count, 1 ):0.0}" );
	}

	private static string Short( Swimmer swimmer ) => System.IO.Path.GetFileNameWithoutExtension( swimmer.Species.Model ?? "?" );

	private void Check( float seconds, Report report )
	{
		const float dt = 0.05f;
		report.Fish += _bodies.Count;
		var speeds = _bodies.ToDictionary( x => x, _ => 0f );
		var last = _bodies.ToDictionary( x => x, x => x.Position );
		foreach ( var swimmer in _bodies )
		{
			swimmer.WatchPosition = swimmer.Position;
			swimmer.WatchTime = _time;
			swimmer.Hovered = 0f;
			swimmer.Path = 0f;
		}

		var steps = (int)( seconds / dt );
		report.StepCount = Math.Max( report.StepCount, steps );
		for ( var step = 0; step < steps; step++ )
		{
			var started = System.Diagnostics.Stopwatch.GetTimestamp();
			Step( dt );
			report.StepMs += System.Diagnostics.Stopwatch.GetElapsedTime( started ).TotalMilliseconds;
			for ( var a = 0; a < _bodies.Count; a++ )
			{
				var swimmer = _bodies[a];
				report.Steps++;
				speeds[swimmer] += swimmer.Speed;
				swimmer.Path += swimmer.Position.Distance( last[swimmer] );
				last[swimmer] = swimmer.Position;
				var outside = Push( swimmer.Position, swimmer.Reach, swimmer.Up, swimmer.Reach ).Length;
				report.WorstOutside = Math.Max( report.WorstOutside, outside );
				if ( outside > 0.05f )
					report.Outside++;

				for ( var b = a + 1; b < _bodies.Count; b++ )
				{
					var other = _bodies[b];
					var overlap = Overlap( swimmer, other, out _ );
					if ( overlap > 0.05f )
					{
						report.Close++;
						report.Closest = Math.Max( report.Closest, overlap );
						var pair = $"{Short( swimmer )}/{Short( other )}";
						report.ClosePairs[pair] = report.ClosePairs.GetValueOrDefault( pair ) + 1;
					}
				}

				if ( _time - swimmer.WatchTime >= 20f )
				{
					// Stuck: it swam under 15% of what it would have at its cruise, outside its hovers. A homebody
					// circling its anemone or rock is fine.
					var swimming = Math.Max( 20f - swimmer.Hovered, 0f );
					if ( swimming > 5f && swimmer.Path < Math.Max( swimmer.Length, swimmer.Cruise * swimming * 0.15f ) )
					{
						report.Still++;
						Log.Info( $"  stuck: {Short( swimmer )} in {GameObject.Name} at {swimmer.Position}, swam {swimmer.Path:0.0} "
							+ $"in {swimming:0} s, moved {swimmer.Position.Distance( swimmer.WatchPosition ):0.0}" );
					}
					swimmer.WatchPosition = swimmer.Position;
					swimmer.WatchTime = _time;
					swimmer.Hovered = 0f;
					swimmer.Path = 0f;
				}
			}
		}

		foreach ( var swimmer in _bodies )
		{
			var name = System.IO.Path.GetFileNameWithoutExtension( swimmer.Species.Model ?? "?" );
			report.Speeds.TryGetValue( name, out var sum );
			report.Speeds[name] = (sum.Speed + speeds[swimmer] / Math.Max( steps, 1 ), sum.Cruise + swimmer.Cruise, sum.Count + 1);
			if ( swimmer.Body is not null )
				Place( swimmer, WorldTransform );
		}
	}
}
