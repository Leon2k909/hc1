using System;

namespace Facepunch;

/// <summary>Vertical landing impact; existing fall thresholds remain in units per second.</summary>
public static class LandingImpactRules
{
	public static float ClosingSpeed( float playerVerticalVelocity, float surfaceVerticalVelocity )
	{
		if ( !float.IsFinite( playerVerticalVelocity ) ) return 0f;
		if ( !float.IsFinite( surfaceVerticalVelocity ) ) surfaceVerticalVelocity = 0f;
		// Positive means the surface is approaching the feet. Separating motion is not an impact.
		return (float)Math.Clamp( (double)surfaceVerticalVelocity - playerVerticalVelocity, 0d, float.MaxValue );
	}
}
