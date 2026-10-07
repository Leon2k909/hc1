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

	/// <summary>
	/// What smoke goes through: people, triggers, the grenades, its own puffs, player clips (an open window's) and bots'
	/// movement boxes. The prefab's <c>CollisionIgnore</c> lists the same for the puffs' own collision.
	/// </summary>
	private static readonly string[] PassThrough = { "trigger", "player", "grenade", "particles", "playerclip", "movement" };

	// Immutable snapshot: no scene/component access from OnParticleStep, which the engine runs in parallel.
	private sealed record Flow( Vector3 Velocity, float Time, float Phase, float Turbulence, float Buoyancy, float Response );
	private Flow Current = new( Vector3.Zero, 0, 0, 12, 18, 1.4f );

	protected override void OnUpdate()
	{
		if ( !Wind.IsValid() ) Wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		Age += Time.Delta;
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
		Current = new Flow( AirVelocity, Age, (Seed & 0xffff) * 0.001f, Turbulence, Buoyancy, AirResponse );
	}

	protected override void OnParticleStep( Particle particle, float delta )
	{
		var flow = Current;
		// Eddies are a continuous spatial field: neighbouring puffs roll together instead of jittering independently.
		var p = particle.Position - flow.Velocity * flow.Time;
		var eddies = Eddy( p / 80f, flow.Time * 0.4f, flow.Phase )
			+ Eddy( p / 29f, flow.Time * 0.7f, flow.Phase + 7.3f ) * 0.35f;
		// Newly emitted warm smoke rises, then cools and is carried mostly by the surrounding air. Vertical
		// eddies fade with that lift: full-strength eddies outlasted it and made cooled puffs bob up and down.
		var lift = flow.Buoyancy * MathF.Exp( -particle.Age / 3.5f );
		var drift = eddies * flow.Turbulence;
		drift.z = eddies.z * MathF.Min( flow.Turbulence * 0.2f, lift * 0.2f );
		var target = flow.Velocity + drift + Vector3.Up * lift;
		particle.Velocity += (target - particle.Velocity) * (1 - MathF.Exp( -delta * flow.Response ));
	}

	private static Vector3 Eddy( Vector3 p, float t, float phase ) => new Vector3(
		MathF.Sin( p.z + t + phase ) + MathF.Cos( p.y - t * 0.7f ),
		MathF.Sin( p.x + t * 0.8f + phase ) + MathF.Cos( p.z + t * 0.6f ),
		MathF.Sin( p.y - t * 0.5f + phase ) + MathF.Cos( p.x + t * 0.9f ) ) * 0.5f;

	// ── Walls ───────────────────────────────────────────────────────────────────
	// A puff is a sprite facing the camera, up to 167 units across. The effect's collision keeps its centre out of walls,
	// but the sprite reached past them: from the other side of a wall, or past a pillar's edge, the part on your side
	// showed (the user's report, 2026-10-01). So each puff keeps to the room round its centre. It shrinks until it reaches
	// no further than the nearest surface, and gets denser by the area it lost, so a corridor or a corner still holds its
	// smoke, in smaller puffs.

	/// <summary>
	/// How far a puff reaches from its centre, as a share of the sprite's width. <c>Particle.Size</c> is the full width:
	/// the renderer passes the shader half of it, which scales a quad of ±10 by a tenth. smoke1.vtex's alpha falls under
	/// 0.05 at 0.43-0.47 of the width out from the centre.
	/// </summary>
	private const float PuffReach = 0.47f;
	/// <summary>How far past a surface a puff may reach: well inside the renderer's DepthFeather (24), which fades it there.</summary>
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
				room.Clearance = Probe( p.Position, room.Spin );
				room.ProbedAt = now;
				room.Probed = true;
				budget--;
			}
		}
		Cursor = (Cursor + ProbesPerFrame) % count;

		foreach ( var p in particles )
		{
			var room = RoomOf( p );
			// The nearest surface is no nearer than it was at the probe, less how far the puff has drifted since.
			var clearance = room.Probed
				? room.Clearance - p.Position.Distance( room.At )
				: VentClearance - p.Position.Distance( VentAt );
			var allowed = MathF.Max( clearance, 0f ) + WallOverlap;
			room.Reach = MathF.Min( allowed, room.Reach + RegrowRate * delta );

			var reach = MathF.Max( p.Size.x, p.Size.y ) * PuffReach;
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
	private float Probe( Vector3 at, float spin )
	{
		var turn = Rotation.FromYaw( spin );
		var nearest = ProbeLength;
		foreach ( var direction in ProbeDirections )
		{
			var length = MathF.Min( nearest, ProbeLength );
			var tr = Scene.Trace.Ray( at, at + turn * direction * length ).WithoutTags( PassThrough ).Run();
			if ( tr.StartedSolid ) return 0f;
			if ( !tr.Hit ) continue;

			var distance = tr.HitPosition.Distance( at );
			if ( tr.Normal.z > 0.7f ) distance += FloorAllowance;
			nearest = MathF.Min( nearest, distance );
		}
		return nearest;
	}
}
