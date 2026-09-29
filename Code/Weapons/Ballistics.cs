namespace Facepunch;

/// <summary>
/// Real bullet paths, solved the way a ballistic calculator solves them (py-ballisticcalc's conventions): a point mass
/// in the ICAO standard atmosphere, slowed by a standard drag function scaled by the bullet's ballistic coefficient,
/// and pulled down by gravity. <see cref="Shootable"/> uses them to put its instant shots where the real bullet lands.
/// </summary>
public static class Ballistics
{
	/// <summary>The standard projectile a ballistic coefficient is published against. Sphere is for buckshot.</summary>
	public enum DragFunction { G1, G7, Sphere }

	/// <summary>One unit is an inch.</summary>
	public const float UnitsPerMeter = 39.3701f;

	/// <summary>The farthest range solved, in metres. Anything farther uses the path at this range.</summary>
	public const int SolvedRange = 1500;

	// ICAO standard atmosphere at sea level: 15 C, 1013.25 hPa, dry. The drag constant is the air's density (1.225 kg/m3)
	// times pi / 8, over 703.07 (1 lb/in2 in kg/m2) since ballistic coefficients are published in lb/in2.
	private const float SpeedOfSound = 340.29f;
	private const float DragConstant = 6.84222e-4f;
	private const float Gravity = 9.80665f;
	private const float TimeStep = 0.001f;

	/// <summary>A load's path when fired level, at every whole metre of range.</summary>
	public sealed class Trajectory
	{
		/// <summary>How far the bullet has fallen below the line the bore points along, in metres.</summary>
		public float[] Drop { get; init; }

		/// <summary>Time of flight, in seconds.</summary>
		public float[] Time { get; init; }

		public float DropAt( float metres ) => Sample( Drop, metres );
		public float TimeAt( float metres ) => Sample( Time, metres );

		private static float Sample( float[] values, float metres )
		{
			var at = Math.Clamp( metres, 0f, values.Length - 1 );
			var i = Math.Min( (int)at, values.Length - 2 );
			return values[i] + (values[i + 1] - values[i]) * (at - i);
		}
	}

	private static readonly Dictionary<(DragFunction, float, float), Trajectory> Solved = new();

	/// <summary>The path of a bullet with this drag function and ballistic coefficient (lb/in2) at this muzzle velocity (m/s).</summary>
	public static Trajectory Get( DragFunction drag, float muzzleVelocity, float ballisticCoefficient )
	{
		var key = (drag, muzzleVelocity, ballisticCoefficient);
		if ( !Solved.TryGetValue( key, out var trajectory ) )
			Solved[key] = trajectory = Solve( drag, muzzleVelocity, ballisticCoefficient );
		return trajectory;
	}

	/// <summary>Flies the bullet level from the muzzle with fourth-order Runge-Kutta steps, noting each metre it passes.</summary>
	private static Trajectory Solve( DragFunction drag, float muzzleVelocity, float ballisticCoefficient )
	{
		var drop = new float[SolvedRange + 1];
		var time = new float[SolvedRange + 1];
		var table = drag switch { DragFunction.G7 => G7, DragFunction.Sphere => GS, _ => G1 };
		var k = DragConstant / ballisticCoefficient;

		// Deceleration: k * Cd(Mach) * speed * velocity, plus gravity.
		(float X, float Y) Acceleration( float vx, float vy )
		{
			var speed = MathF.Sqrt( vx * vx + vy * vy );
			var retard = k * DragCoefficient( table, speed / SpeedOfSound ) * speed;
			return (-retard * vx, -retard * vy - Gravity);
		}

		float x = 0f, y = 0f, vx = muzzleVelocity, vy = 0f, t = 0f;
		var metre = 1;
		while ( metre <= SolvedRange && t < 30f && vx > 1f )
		{
			var a1 = Acceleration( vx, vy );
			var a2 = Acceleration( vx + 0.5f * TimeStep * a1.X, vy + 0.5f * TimeStep * a1.Y );
			var a3 = Acceleration( vx + 0.5f * TimeStep * a2.X, vy + 0.5f * TimeStep * a2.Y );
			var a4 = Acceleration( vx + TimeStep * a3.X, vy + TimeStep * a3.Y );
			var nx = x + TimeStep / 6f * (vx + 2f * (vx + 0.5f * TimeStep * a1.X) + 2f * (vx + 0.5f * TimeStep * a2.X) + (vx + TimeStep * a3.X));
			var ny = y + TimeStep / 6f * (vy + 2f * (vy + 0.5f * TimeStep * a1.Y) + 2f * (vy + 0.5f * TimeStep * a2.Y) + (vy + TimeStep * a3.Y));
			vx += TimeStep / 6f * (a1.X + 2f * a2.X + 2f * a3.X + a4.X);
			vy += TimeStep / 6f * (a1.Y + 2f * a2.Y + 2f * a3.Y + a4.Y);

			for ( ; metre <= SolvedRange && nx >= metre; metre++ )
			{
				var f = (metre - x) / (nx - x);
				drop[metre] = -(y + f * (ny - y));
				time[metre] = t + f * TimeStep;
			}

			x = nx;
			y = ny;
			t += TimeStep;
		}

		// A bullet that stopped short (buckshot) keeps its last point.
		for ( ; metre <= SolvedRange; metre++ )
		{
			drop[metre] = drop[metre - 1];
			time[metre] = time[metre - 1];
		}

		return new Trajectory { Drop = drop, Time = time };
	}

	/// <summary>A drag table's drag coefficient at a Mach number, straight between its points.</summary>
	private static float DragCoefficient( float[] table, float mach )
	{
		if ( mach <= table[0] ) return table[1];
		for ( int i = 2; i < table.Length; i += 2 )
		{
			if ( mach > table[i] ) continue;
			var t = (mach - table[i - 2]) / (table[i] - table[i - 2]);
			return table[i - 1] + (table[i + 1] - table[i - 1]) * t;
		}
		return table[^1];
	}

	// The standard drag functions as (Mach, drag coefficient) pairs: G1 and G7 as JBM Ballistics publishes them
	// (mcg1.txt, mcg7.txt), and py-ballisticcalc's sphere table.
	private static readonly float[] G1 =
	[
		0f, 0.2629f, 0.05f, 0.2558f, 0.1f, 0.2487f, 0.15f, 0.2413f, 0.2f, 0.2344f, 0.25f, 0.2278f,
		0.3f, 0.2214f, 0.35f, 0.2155f, 0.4f, 0.2104f, 0.45f, 0.2061f, 0.5f, 0.2032f, 0.55f, 0.202f,
		0.6f, 0.2034f, 0.7f, 0.2165f, 0.725f, 0.223f, 0.75f, 0.2313f, 0.775f, 0.2417f, 0.8f, 0.2546f,
		0.825f, 0.2706f, 0.85f, 0.2901f, 0.875f, 0.3136f, 0.9f, 0.3415f, 0.925f, 0.3734f, 0.95f, 0.4084f,
		0.975f, 0.4448f, 1f, 0.4805f, 1.025f, 0.5136f, 1.05f, 0.5427f, 1.075f, 0.5677f, 1.1f, 0.5883f,
		1.125f, 0.6053f, 1.15f, 0.6191f, 1.2f, 0.6393f, 1.25f, 0.6518f, 1.3f, 0.6589f, 1.35f, 0.6621f,
		1.4f, 0.6625f, 1.45f, 0.6607f, 1.5f, 0.6573f, 1.55f, 0.6528f, 1.6f, 0.6474f, 1.65f, 0.6413f,
		1.7f, 0.6347f, 1.75f, 0.628f, 1.8f, 0.621f, 1.85f, 0.6141f, 1.9f, 0.6072f, 1.95f, 0.6003f,
		2f, 0.5934f, 2.05f, 0.5867f, 2.1f, 0.5804f, 2.15f, 0.5743f, 2.2f, 0.5685f, 2.25f, 0.563f,
		2.3f, 0.5577f, 2.35f, 0.5527f, 2.4f, 0.5481f, 2.45f, 0.5438f, 2.5f, 0.5397f, 2.6f, 0.5325f,
		2.7f, 0.5264f, 2.8f, 0.5211f, 2.9f, 0.5168f, 3f, 0.5133f, 3.1f, 0.5105f, 3.2f, 0.5084f,
		3.3f, 0.5067f, 3.4f, 0.5054f, 3.5f, 0.504f, 3.6f, 0.503f, 3.7f, 0.5022f, 3.8f, 0.5016f,
		3.9f, 0.501f, 4f, 0.5006f, 4.2f, 0.4998f, 4.4f, 0.4995f, 4.6f, 0.4992f, 4.8f, 0.499f,
		5f, 0.4988f,
	];

	private static readonly float[] G7 =
	[
		0f, 0.1198f, 0.05f, 0.1197f, 0.1f, 0.1196f, 0.15f, 0.1194f, 0.2f, 0.1193f, 0.25f, 0.1194f,
		0.3f, 0.1194f, 0.35f, 0.1194f, 0.4f, 0.1193f, 0.45f, 0.1193f, 0.5f, 0.1194f, 0.55f, 0.1193f,
		0.6f, 0.1194f, 0.65f, 0.1197f, 0.7f, 0.1202f, 0.725f, 0.1207f, 0.75f, 0.1215f, 0.775f, 0.1226f,
		0.8f, 0.1242f, 0.825f, 0.1266f, 0.85f, 0.1306f, 0.875f, 0.1368f, 0.9f, 0.1464f, 0.925f, 0.166f,
		0.95f, 0.2054f, 0.975f, 0.2993f, 1f, 0.3803f, 1.025f, 0.4015f, 1.05f, 0.4043f, 1.075f, 0.4034f,
		1.1f, 0.4014f, 1.125f, 0.3987f, 1.15f, 0.3955f, 1.2f, 0.3884f, 1.25f, 0.381f, 1.3f, 0.3732f,
		1.35f, 0.3657f, 1.4f, 0.358f, 1.5f, 0.344f, 1.55f, 0.3376f, 1.6f, 0.3315f, 1.65f, 0.326f,
		1.7f, 0.3209f, 1.75f, 0.316f, 1.8f, 0.3117f, 1.85f, 0.3078f, 1.9f, 0.3042f, 1.95f, 0.301f,
		2f, 0.298f, 2.05f, 0.2951f, 2.1f, 0.2922f, 2.15f, 0.2892f, 2.2f, 0.2864f, 2.25f, 0.2835f,
		2.3f, 0.2807f, 2.35f, 0.2779f, 2.4f, 0.2752f, 2.45f, 0.2725f, 2.5f, 0.2697f, 2.55f, 0.267f,
		2.6f, 0.2643f, 2.65f, 0.2615f, 2.7f, 0.2588f, 2.75f, 0.2561f, 2.8f, 0.2533f, 2.85f, 0.2506f,
		2.9f, 0.2479f, 2.95f, 0.2451f, 3f, 0.2424f, 3.1f, 0.2368f, 3.2f, 0.2313f, 3.3f, 0.2258f,
		3.4f, 0.2205f, 3.5f, 0.2154f, 3.6f, 0.2106f, 3.7f, 0.206f, 3.8f, 0.2017f, 3.9f, 0.1975f,
		4f, 0.1935f, 4.2f, 0.1861f, 4.4f, 0.1793f, 4.6f, 0.173f, 4.8f, 0.1672f, 5f, 0.1618f,
	];

	private static readonly float[] GS =
	[
		0f, 0.4662f, 0.05f, 0.4689f, 0.1f, 0.4717f, 0.15f, 0.4745f, 0.2f, 0.4772f, 0.25f, 0.48f,
		0.3f, 0.4827f, 0.35f, 0.4852f, 0.4f, 0.4882f, 0.45f, 0.492f, 0.5f, 0.497f, 0.55f, 0.508f,
		0.6f, 0.526f, 0.65f, 0.559f, 0.7f, 0.592f, 0.75f, 0.6258f, 0.8f, 0.661f, 0.85f, 0.6985f,
		0.9f, 0.737f, 0.95f, 0.7757f, 1f, 0.814f, 1.05f, 0.8512f, 1.1f, 0.887f, 1.15f, 0.921f,
		1.2f, 0.951f, 1.25f, 0.974f, 1.3f, 0.991f, 1.35f, 0.999f, 1.4f, 1.003f, 1.45f, 1.006f,
		1.5f, 1.008f, 1.55f, 1.009f, 1.6f, 1.009f, 1.65f, 1.009f, 1.7f, 1.009f, 1.75f, 1.008f,
		1.8f, 1.007f, 1.85f, 1.006f, 1.9f, 1.004f, 1.95f, 1.0025f, 2f, 1.001f, 2.05f, 0.999f,
		2.1f, 0.997f, 2.15f, 0.9956f, 2.2f, 0.994f, 2.25f, 0.9916f, 2.3f, 0.989f, 2.35f, 0.9869f,
		2.4f, 0.985f, 2.45f, 0.983f, 2.5f, 0.981f, 2.55f, 0.979f, 2.6f, 0.977f, 2.65f, 0.975f,
		2.7f, 0.973f, 2.75f, 0.971f, 2.8f, 0.969f, 2.85f, 0.967f, 2.9f, 0.965f, 2.95f, 0.963f,
		3f, 0.961f, 3.05f, 0.9589f, 3.1f, 0.957f, 3.15f, 0.9555f, 3.2f, 0.954f, 3.25f, 0.952f,
		3.3f, 0.95f, 3.35f, 0.9485f, 3.4f, 0.947f, 3.45f, 0.945f, 3.5f, 0.943f, 3.55f, 0.9414f,
		3.6f, 0.94f, 3.65f, 0.9385f, 3.7f, 0.937f, 3.75f, 0.9355f, 3.8f, 0.934f, 3.85f, 0.9325f,
		3.9f, 0.931f, 3.95f, 0.9295f, 4f, 0.928f,
	];
}
