namespace Facepunch;

/// <summary>
/// Advects smoke with wind and smooth eddies. This is a particle approximation, not a fluid solver.
/// Only numeric particle work runs on the particle threads; scene queries run on the main thread.
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
				.WithoutTags( "trigger", "player", "grenade", "particles" ).Run().Hit;
			var covered = Scene.Trace.Ray( sample, sample + Vector3.Up * 256f )
				.WithoutTags( "trigger", "player", "grenade", "particles" ).Run().Hit;
			ExposureTarget = (blocked ? 0.12f : 1f) * (covered ? 0.2f : 1f);
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
		// Newly emitted warm smoke rises, then cools and is carried mostly by the surrounding air.
		var lift = flow.Buoyancy * MathF.Exp( -particle.Age / 3.5f );
		var target = flow.Velocity + eddies * flow.Turbulence + Vector3.Up * lift;
		particle.Velocity += (target - particle.Velocity) * (1 - MathF.Exp( -delta * flow.Response ));
	}

	private static Vector3 Eddy( Vector3 p, float t, float phase ) => new Vector3(
		MathF.Sin( p.z + t + phase ) + MathF.Cos( p.y - t * 0.7f ),
		MathF.Sin( p.x + t * 0.8f + phase ) + MathF.Cos( p.z + t * 0.6f ),
		MathF.Sin( p.y - t * 0.5f + phase ) + MathF.Cos( p.x + t * 0.9f ) ) * 0.5f;
}
