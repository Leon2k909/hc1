using System;

namespace Facepunch;

/// <summary>Bounded gameplay blast impulse; a radial falloff, not a pressure-wave simulation.</summary>
public static class BlastImpulseRules
{
	/// <summary>
	/// Strongest near the source, fading to zero at the blast radius. Preserve the old force envelope
	/// (radius * 50) and its midpoint magnitude while correcting the previously reversed falloff.
	/// </summary>
	public static float Magnitude( float distance, float radius )
	{
		if ( !float.IsFinite( distance ) || !float.IsFinite( radius ) || radius <= 0f ) return 0f;
		var remaining = Math.Max( 0d, (double)radius - Math.Max( 0f, distance ) );
		return (float)Math.Min( remaining * 50d, float.MaxValue );
	}
}
