namespace Facepunch;

/// <summary>
/// Advects smoke with wind and smooth eddies, and keeps each puff inside the space it's in. This is a particle
/// approximation, not a fluid solver. Only numeric particle work runs on the particle threads; scene queries run on the
/// main thread (<see cref="OnUpdate"/>, and <see cref="OnAfterStep"/>, which the engine calls there once the threaded step
/// is done).
/// </summary>
[Title( "Smoke Airflow" )]
public sealed class SmokeSimulation : ParticleController
{
	[Property] public int Seed { get; set; }
	[Property, Range( 0, 40 )] public float Turbulence { get; set; } = 12f;
	[Property, Range( 0, 60 )] public float Buoyancy { get; set; } = 18f;
	[Property, Range( 0.1f, 5 )] public float AirResponse { get; set; } = 1.4f;

	public Vector3 AirVelocity { get; private set; }
	public float Exposure { get; private set; } = 1f;
	private WorldWind Wind;
	private TimeUntil NextExposureCheck;
	private float ExposureTarget = 1f;
	private float Age;
	private Vector3 AirOffset;

	/// <summary>
	/// What smoke goes through: people, triggers, the grenades, its own puffs, player clips (an open window's) and bots'
	/// movement boxes. The prefab's <c>CollisionIgnore</c> lists the same for the puffs' own collision.
	/// </summary>
	private static readonly string[] PassThrough = { "trigger", "player", "grenade", "particles", "playerclip", "movement" };

	// Immutable snapshot: no scene/component access from OnParticleStep, which the engine runs in parallel.
	private sealed record Flow( Vector3 Velocity, Vector3 Offset, float Time, float Phase, float Turbulence,
		float Buoyancy, float Response, float Seconds );
	private Flow Current = new( Vector3.Zero, Vector3.Zero, 0, 0, 12, 18, 1.4f, 0 );

	// The volume renderer (SmokeRendering, hc1_smoke.shader) drew nothing in the engine (2026-10-12: 200 puffs queued
	// for the camera, nothing on screen), so the smoke is drawn by the prefab's sprite renderer until it's fixed.
	// protected override void OnStart() => SmokeRendering.Ensure( Scene );

	protected override void OnUpdate()
	{
		if ( !Wind.IsValid() ) Wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		var wind = Wind.IsValid() && Wind.Active ? Wind.Sample( WorldPosition ) : Vector3.Zero;
		if ( NextExposureCheck )
		{
			NextExposureCheck = 0.25f;
			// A short upwind ray measures shelter; the overhead ray reduces the outdoor breeze inside rooms.
			var sample = WorldPosition + Vector3.Up * 16f;
			var direction = wind.WithZ( 0 ).Normal;
			var blocked = direction.LengthSquared > 0.01f && Scene.Trace.Ray( sample, sample - direction * 256f )
				.WithoutTags( PassThrough ).Run().Hit;
			var covered = Scene.Trace.Ray( sample, sample + Vector3.Up * 256f )
				.WithoutTags( PassThrough ).Run().Hit;
			ExposureTarget = (blocked ? 0.12f : 1f) * (covered ? 0.2f : 1f);

			// New puffs leave the vent, so until they're probed themselves they go by its room.
			VentAt = WorldPosition;
			VentClearance = Probe( VentAt, Age * 97f );
		}
		Exposure += (ExposureTarget - Exposure) * (1 - MathF.Exp( -Time.Delta * 5f ));
		AirVelocity = wind * Exposure;
	}

	protected override void OnBeforeStep( float delta )
	{
		Age += delta;
		// Integrate the air's displacement. Multiplying a changing gust by the effect's total age made the field jump.
		AirOffset += AirVelocity * delta;
		Current = new Flow( AirVelocity, AirOffset, Age, (Seed & 0xffff) * 0.001f,
			Turbulence, Buoyancy, AirResponse, delta );
	}

	protected override void OnParticleStep( Particle particle, float lifeDelta )
	{
		var flow = Current;
		// OnParticleStep receives normalized life progress, NOT elapsed seconds. Only OnBeforeStep supplies the timestep.
		particle.Velocity = SmokeMath.Advect( particle.Velocity, particle.Position, flow.Offset, flow.Velocity,
			flow.Time, particle.Age, flow.Phase, flow.Turbulence, flow.Buoyancy, flow.Response,
			flow.Seconds * particle.TimeScale );
	}

	// ── Walls ───────────────────────────────────────────────────────────────────
	// Centre collisions alone cannot keep a wide puff from reaching through a wall. Keep its volume within the room,
	// increasing density as it loses area so tight corridors still hold their smoke.
	/// <summary>A small overlap at boundaries; the renderer clips the visible volume at the surface depth.</summary>
	private const float WallOverlap = 6f;
	/// <summary>
	/// Room a floor gives on top of that. A puff sunk into the floor it's over looks like smoke lying on it: from the same
	/// floor the floor hides what's under it. Only from the storey below could it show, and the floor's own thickness
	/// takes most of this. Held to the floor as strictly as to the walls, the cloud's base would be small, dense lumps.
	/// </summary>
	private const float FloorAllowance = 32f;
	/// <summary>Probes look this far: past the largest puff's reach (145 x 1.15 x 0.47 = 79).</summary>
	private const float ProbeLength = 90f;
	/// <summary>Puffs probed a frame, at most, at 26 rays each.</summary>
	private const int ProbesPerFrame = 10;
	/// <summary>A puff is probed again once it's this far from where it was probed.</summary>
	private const float ReprobeDistance = 16f;
	/// <summary>Or this long after, for doors that open or shut.</summary>
	private const float ReprobeTime = 1f;
	/// <summary>How fast a puff grows back into room it's found (units of reach a second). It shrinks at once.</summary>
	private const float RegrowRate = 30f;
	/// <summary>A squeezed puff gets denser by the area it lost, up to this much and to MaxAlpha at most.</summary>
	private const float MaxDensityGain = 2.5f;
	private const float MaxAlpha = 0.85f;

	/// <summary>The probes' directions: a level ring every 30 degrees, a ring of 6 at 35 degrees up and one at 35 down
	/// (each turned 15 degrees from the last, so a pillar or a door jamb between two rays of one ring meets the next's),
	/// then straight up and down.</summary>
	private static readonly Vector3[] ProbeDirections = BuildProbeDirections();

	private static Vector3[] BuildProbeDirections()
	{
		var directions = new List<Vector3>();
		for ( var i = 0; i < 12; i++ )
			directions.Add( new Angles( 0f, i * 30f, 0f ).Forward );
		for ( var i = 0; i < 6; i++ )
			directions.Add( new Angles( -35f, 15f + i * 60f, 0f ).Forward );
		for ( var i = 0; i < 6; i++ )
			directions.Add( new Angles( 35f, 45f + i * 60f, 0f ).Forward );
		directions.Add( Vector3.Up );
		directions.Add( Vector3.Down );
		return directions.ToArray();
	}

	private sealed class Room
	{
		/// <summary>Where it was last probed, and how far the nearest surface was from there.</summary>
		public Vector3 At;
		public float Clearance;
		public float ProbedAt;
		public bool Probed;
		/// <summary>How far it may reach now, eased up as it finds room.</summary>
		public float Reach = 1e6f;
		/// <summary>Turns its probes, so neighbouring puffs don't all miss the same edge.</summary>
		public float Spin;
		public readonly List<SmokeMath.Surface> Surfaces = new();
	}

	private readonly Dictionary<Particle, Room> Rooms = new();
	private readonly HashSet<Particle> Live = new();
	private Vector3 VentAt;
	private float VentClearance = ProbeLength;
	private int Cursor;

	protected override void OnParticleDestroyed( Particle p )
	{
		Rooms.Remove( p );
	}

	/// <summary>
	/// The effect has set each puff's size and alpha for this frame by now (its Scale and Alpha curves run after
	/// OnParticleStep), so this is where they're held to the room.
	/// </summary>
	protected override void OnAfterStep( float delta )
	{
		var effect = ParticleEffect;
		if ( !effect.IsValid() ) return;

		var particles = effect.Particles;
		var count = particles.Count;
		if ( Rooms.Count > count + 64 ) Prune( particles );
		if ( count == 0 ) return;

		var now = Time.Now;
		Cursor %= count;

		// New puffs first, then those that have drifted or gone stale, a few a frame.
		var budget = ProbesPerFrame;
		for ( var pass = 0; pass < 2 && budget > 0; pass++ )
		{
			for ( var i = 0; i < count && budget > 0; i++ )
			{
				var p = particles[(Cursor + i) % count];
				var room = RoomOf( p );
				var due = pass == 0
					? !room.Probed
					: now - room.ProbedAt > ReprobeTime || p.Position.DistanceSquared( room.At ) > ReprobeDistance * ReprobeDistance;
				if ( !due ) continue;

				room.At = p.Position;
				room.Clearance = Probe( p.Position, room.Spin, room.Surfaces );
				room.ProbedAt = now;
				room.Probed = true;
				budget--;
			}
		}
		Cursor = (Cursor + ProbesPerFrame) % count;

		foreach ( var p in particles )
		{
			var room = RoomOf( p );
			// Track distance along surface normals. The old distance-from-probe bound shrank puffs even when they moved
			// parallel to a flat floor or wall, then let them grow at the next probe: a repeating visual bob/pop.
			var clearance = VentClearance - p.Position.Distance( VentAt );
			if ( room.Probed )
			{
				clearance = room.Clearance <= 0f ? 0f : ProbeLength;
				foreach ( var surface in room.Surfaces )
					clearance = MathF.Min( clearance, surface.Clearance( p.Position ) );
			}
			var allowed = MathF.Max( clearance, 0f ) + WallOverlap;
			room.Reach = MathF.Min( allowed, room.Reach + RegrowRate * delta );

			var reach = MathF.Max( p.Size.x, p.Size.y ) * SmokeMath.PuffReach;
			if ( reach <= room.Reach ) continue;

			var shrink = room.Reach / reach;
			p.Size *= shrink;
			var denser = MathF.Min( p.Alpha * MathF.Min( 1f / (shrink * shrink), MaxDensityGain ), MaxAlpha );
			p.Alpha = MathF.Max( p.Alpha, denser );
		}
	}

	private Room RoomOf( Particle p )
	{
		if ( Rooms.TryGetValue( p, out var room ) ) return room;
		room = new Room { Spin = Game.Random.Float( 0f, 30f ) };
		Rooms[p] = room;
		return room;
	}

	/// <summary>Drops rooms whose puffs have gone without the effect saying so (it was cleared).</summary>
	private void Prune( List<Particle> particles )
	{
		Live.Clear();
		foreach ( var p in particles ) Live.Add( p );
		foreach ( var p in Rooms.Keys.Where( p => !Live.Contains( p ) ).ToList() ) Rooms.Remove( p );
		Live.Clear();
	}

	/// <summary>How far the nearest surface is from <paramref name="at"/>, up to ProbeLength: the nearest point any of
	/// the probes' rays meets, turned by <paramref name="spin"/> degrees. Floors count FloorAllowance further off.</summary>
	private float Probe( Vector3 at, float spin, List<SmokeMath.Surface> surfaces = null )
	{
		surfaces?.Clear();
		var turn = Rotation.FromYaw( spin );
		var nearest = ProbeLength;
		foreach ( var direction in ProbeDirections )
		{
			var length = MathF.Min( nearest, ProbeLength );
			var tr = Scene.Trace.Ray( at, at + turn * direction * length ).WithoutTags( PassThrough ).Run();
			if ( tr.StartedSolid )
			{
				surfaces?.Clear();
				return 0f;
			}
			if ( !tr.Hit ) continue;

			var surface = new SmokeMath.Surface( tr.HitPosition, tr.Normal, tr.Normal.z > 0.7f ? FloorAllowance : 0f );
			surfaces?.Add( surface );
			var distance = surface.Clearance( at );
			nearest = MathF.Min( nearest, distance );
		}
		return nearest;
	}
}
