using System;

namespace Facepunch;

/// <summary>Cosmetic ejection velocities in weapon axes (inches/second), not measured firearm data.</summary>
public static class CasingEjectionRules
{
	public readonly record struct LocalVelocity( float Forward, float Right, float Up );

	public static bool EjectsDownward( string weaponPath ) => string.Equals(
		weaponPath?.Replace( '\\', '/' ), "weapons/p90/p90.equip", StringComparison.OrdinalIgnoreCase );

	private static float Unit( float value ) => float.IsFinite( value ) ? Math.Clamp( value, 0f, 1f ) : 0.5f;

	/// <summary>Samples are independent random values in [0,1]. Conventional guns keep their existing launch ranges.</summary>
	public static LocalVelocity Sample( string weaponPath, float side, float lift, float rear )
	{
		side = Unit( side );
		lift = Unit( lift );
		rear = Unit( rear );
		if ( EjectsDownward( weaponPath ) )
			return new( -5f + rear * 10f, -5f + side * 10f, -35f - lift * 20f );

		return new( -12f - rear * 18f, 85f + side * 30f, 55f + lift * 25f );
	}
}
