namespace Facepunch;

/// <summary>Numeric smoke transport and visibility, shared by the simulation and its regression checks.</summary>
internal static class SmokeMath
{
	public const float PuffReach = 0.47f;

	public static Vector3 Advect( Vector3 velocity, Vector3 position, Vector3 airOffset, Vector3 wind,
		float time, float age, float phase, float turbulence, float buoyancy, float response, float seconds )
	{
		if ( seconds <= 0f ) return velocity;
		var p = position - airOffset;
		var eddies = Eddy( p / 80f, time * 0.4f, phase )
			+ Eddy( p / 29f, time * 0.7f, phase + 7.3f ) * 0.35f;
		var lift = buoyancy * MathF.Exp( -age / 3.5f );
		var drift = eddies * turbulence;
		// The vertical field dies away with the heat, rather than pushing cold puffs down and back up.
		drift.z = eddies.z * MathF.Min( turbulence * 0.2f, lift * 0.2f );
		var target = wind + drift + Vector3.Up * lift;
		return velocity + (target - velocity) * (1f - MathF.Exp( -seconds * response ));
	}

	private static Vector3 Eddy( Vector3 p, float t, float phase ) => new Vector3(
		MathF.Sin( p.z + t + phase ) + MathF.Cos( p.y - t * 0.7f ),
		MathF.Sin( p.x + t * 0.8f + phase ) + MathF.Cos( p.z + t * 0.6f ),
		MathF.Sin( p.y - t * 0.5f + phase ) + MathF.Cos( p.x + t * 0.9f ) ) * 0.5f;

	public readonly record struct Surface( Vector3 Position, Vector3 Normal, float Allowance )
	{
		public float Clearance( Vector3 at ) => Vector3.Dot( at - Position, Normal ) + Allowance;
	}

	/// <summary>
	/// Integrates a smooth spherical puff only along the visible part of a ray. An object in front contributes no smoke;
	/// one within the puff gets just the smoke before its surface. The shader uses the same polynomial integral.
	/// </summary>
	public static float OpticalDepth( Vector3 camera, Vector3 direction, Vector3 centre, float radius,
		float surfaceDistance, float alpha )
	{
		if ( radius <= 0f || surfaceDistance <= 0f || alpha <= 0f ) return 0f;
		var offset = centre - camera;
		var along = Vector3.Dot( offset, direction );
		var perpendicularSquared = MathF.Max( 0f, offset.LengthSquared - along * along );
		var heightSquared = 1f - perpendicularSquared / (radius * radius);
		if ( heightSquared <= 0f ) return 0f;
		var height = MathF.Sqrt( heightSquared );
		var start = MathF.Max( -height, -along / radius );
		var end = MathF.Min( height, (surfaceDistance - along) / radius );
		if ( end <= start ) return 0f;
		var path = (Integral( end, heightSquared ) - Integral( start, heightSquared )) * (15f / 16f);
		return -MathF.Log( 1f - Math.Clamp( alpha, 0f, 0.995f ) ) * MathF.Max( path, 0f );
	}

	private static float Integral( float u, float h2 ) => u * (h2 * h2 - u * u * (2f / 3f) * h2 + u * u * u * u / 5f);
}
