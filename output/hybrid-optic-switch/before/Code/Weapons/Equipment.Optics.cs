using Facepunch.Gunsmith;

namespace Facepunch;

public partial class Equipment
{
	/// <summary>Use the fitted sight's alignment, including factory optics on weapons picked up from bots.</summary>
	public bool TryGetOpticAim( out GunsmithPart optic )
	{
		optic = null;
		if ( ViewModel.IsValid() )
		{
			optic = ViewModel.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
				.FirstOrDefault( point => point.Category == GunsmithPartType.Optic )?.CurrentPart;
		}
		else if ( Resource.IsValid() )
		{
			if ( ApplySavedAttachments )
				GunsmithLoadoutManager.TryGetAttachment( Resource, GunsmithPartType.Optic, out optic );
			else if ( Resource.ViewModelPrefab.IsValid() )
				optic = Resource.ViewModelPrefab.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
					.FirstOrDefault( point => point.Category == GunsmithPartType.Optic )?.CurrentPart;
		}

		return optic.IsValid() && optic.OverrideAimOffset;
	}

	/// <summary>
	/// The field of view the guns' <see cref="AimFovOffset"/>s are set at: the Field Of View setting's default.
	/// </summary>
	public const float ReferenceFov = 85f;

	/// <summary>
	/// Main camera zoom while aiming, from <paramref name="baseFov"/>. Magnified optics only zoom the main view slightly;
	/// the magnified image is drawn inside the lens by <see cref="OpticZoom"/> (picture-in-picture, like MW2022).
	/// </summary>
	public float GetAimFovOffset( float baseFov )
	{
		var magnification = OffsetMagnification( AimFovOffset );
		if ( TryGetOpticAim( out var optic ) && optic.OpticMagnification > 1f )
			magnification *= OpticZoom.ViewMagnification;

		return AimFov( baseFov, magnification ) - baseFov;
	}

	/// <summary>
	/// The field of view while aiming with <paramref name="magnification"/>, from <paramref name="hipFov"/>.
	/// Settings → Video → ADS Field Of View: Affected zooms the player's own field of view, so a wider one stays wider
	/// aiming; Independent aims at what the default field of view would, whatever the player's is.
	/// </summary>
	public static float AimFov( float hipFov, float magnification )
	{
		var independent = GameSettingsSystem.Current?.IndependentAdsFov ?? false;
		return ZoomFov( independent ? ReferenceFov : hipFov, magnification );
	}

	/// <summary>
	/// The magnification that narrows <see cref="ReferenceFov"/> by <paramref name="offset"/> degrees (negative to
	/// narrow), so an offset set at the default zooms any field of view by as much.
	/// </summary>
	public static float OffsetMagnification( float offset )
	{
		var zoomed = (ReferenceFov + offset).Clamp( 1f, 170f );
		return MathF.Tan( ReferenceFov * MathF.PI / 360f ) / MathF.Tan( zoomed * MathF.PI / 360f );
	}

	public static float ZoomFov( float fov, float magnification )
	{
		var unzoomed = fov.Clamp( 10f, 150f );
		return 2f * MathF.Atan( MathF.Tan( unzoomed * MathF.PI / 360f ) / magnification ) * 180f / MathF.PI;
	}

	/// <summary>
	/// The range the sights are zeroed at, in metres: the fitted optic's tuned zero (<see cref="OpticTuning"/>), or
	/// <paramref name="factory"/>. Only the owner's own build has a tune; a gun picked up off the floor shoots at its factory zero.
	/// </summary>
	public float GetSightZero( float factory )
	{
		if ( !ApplySavedAttachments || !Resource.IsValid() || !TryGetOpticAim( out var optic ) || !OpticTuning.IsTunable( optic ) )
			return factory;
		var zero = GunsmithLoadoutManager.GetOpticZero( Resource, optic );
		return zero > 0 ? zero : factory;
	}
}
