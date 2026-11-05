using System;

namespace Facepunch;

/// <summary>Conservative gameplay damage loss per inch crossed, not cartridge-specific terminal ballistics.</summary>
public static class PenetrationDamageRules
{
	public static float LossPerUnit( string material ) => material?.ToLowerInvariant() switch
	{
		"wood" => 0.125f,
		"plastic" => 0.175f,
		"metal.sheet" => 3.2f,
		// Map window collision is much thicker than the real pane; keep this loss modest.
		"glass" or "glass.pane" => 0.05f,
		"fabric" or "paper" or "cardboard" => 0.1f,
		_ => 0f
	};

	public static float RetainedFraction( float lossPerUnit, float thickness )
	{
		if ( !float.IsFinite( lossPerUnit ) || !float.IsFinite( thickness ) || lossPerUnit <= 0f || thickness <= 0f ) return 1f;
		return Math.Clamp( 1f - lossPerUnit * thickness, 0f, 1f );
	}
}
