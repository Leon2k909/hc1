using Facepunch.Gunsmith;

namespace Facepunch;

public partial class Equipment
{
	/// <summary>Local camera configuration; never changes the weapon's original aim defaults.</summary>
	public bool TryGetOpticAim( out GunsmithPart optic )
	{
		optic = null;
		return ApplySavedAttachments && Resource.IsValid()
			&& GunsmithLoadoutManager.TryGetAttachment( Resource, GunsmithPartType.Optic, out optic )
			&& optic.IsValid() && optic.OverrideAimOffset;
	}

	/// <summary>
	/// Main camera zoom while aiming. Magnified optics only zoom the main view slightly; the magnified image is
	/// drawn inside the lens by <see cref="OpticZoom"/> (picture-in-picture, like MW2022).
	/// </summary>
	public float GetAimFovOffset( float baseFov )
	{
		if ( !TryGetOpticAim( out var optic ) || optic.OpticMagnification <= 1f )
			return AimFovOffset;

		return ZoomFov( baseFov + AimFovOffset, OpticZoom.ViewMagnification ) - baseFov;
	}

	public static float ZoomFov( float fov, float magnification )
	{
		var unzoomed = fov.Clamp( 10f, 150f );
		return 2f * MathF.Atan( MathF.Tan( unzoomed * MathF.PI / 360f ) / magnification ) * 180f / MathF.PI;
	}
}
