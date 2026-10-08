namespace Facepunch;

/// <summary>The clear part of a scope's image as the eye leaves its exit pupil.</summary>
public readonly record struct ScopeEyeBox( Vector2 Offset, float Radius, float Blackout )
{
	/// <param name="eyeOffset">Eye displacement to the right/down, measured in eyepiece radii.</param>
	/// <param name="reliefError">Distance from the settled eye relief, relative to its usable range.</param>
	/// <param name="magnification">The optic's power, before the main camera's slight aim zoom.</param>
	public static ScopeEyeBox Calculate( Vector2 eyeOffset, float reliefError, float magnification )
	{
		// Higher power has a smaller exit pupil, so the same movement cuts further into the picture.
		var power = ((magnification.Clamp( 2f, 8f ) - 2f) / 6f);
		var pupil = 0.55f - power * 0.25f;
		var error = eyeOffset / pupil;
		var lateral = error.Length;
		var relief = MathF.Abs( reliefError ).Clamp( 0f, 2f );
		var offset = error * 0.65f;
		if ( offset.Length > 1.6f ) offset = offset.Normal * 1.6f;
		var radius = (1f - lateral * 0.12f - relief * 0.3f).Clamp( 0.25f, 1f );
		var blackout = MathF.Max( (lateral - 1.65f) / 0.75f, (relief - 0.9f) / 0.65f ).Clamp( 0f, 1f );
		return new ScopeEyeBox( offset, radius, blackout );
	}
}
