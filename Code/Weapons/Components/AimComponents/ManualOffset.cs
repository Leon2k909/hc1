namespace Facepunch;

public interface IViewModelOffset
{
	public Vector3 PositionOffset { get; }
	public Angles AngleOffset { get; }
}

[Title( "ADS (w/ Aim Offset)" ), Group( "Weapon Components" )]
public partial class ManualOffset : Aimable, IViewModelOffset
{
	[Property] public Vector3 AimOffset { get; set; }
	[Property] public Angles AimAngleOffset { get; set; }

	/// <summary>
	/// Added to a fitted optic's <see cref="Gunsmith.GunsmithPart.OpticAimOffset"/>, which is calibrated on the M4:
	/// how far this weapon's ADS pose and optic mount put the sight line from where the M4's do.
	/// </summary>
	[Property] public Vector3 OpticAimCorrection { get; set; }

	protected override void OnStart()
	{
		base.OnStart();
		IronSightCalibration.Verify( Equipment, this );
	}

	protected override void OnUpdate()
	{
		base.OnUpdate();
		if ( IsAiming && Equipment.IsValid() && Player.IsValid() && Player.IsLocallyControlled
			&& Equipment.TryGetOpticAim( out var optic ) )
		{
			Player.AimDampening /= optic.OpticMagnification.Clamp( 1f, 8f );
		}
	}

	Vector3 IViewModelOffset.PositionOffset => IsAiming
		? Equipment.IsValid() && Equipment.TryGetOpticAim( out var optic ) ? optic.OpticAimOffset + OpticAimCorrection : AimOffset
		: Vector3.Zero;
	Angles IViewModelOffset.AngleOffset => IsAiming
		? Equipment.IsValid() && Equipment.TryGetOpticAim( out var optic ) ? optic.OpticAimAngles : AimAngleOffset
		: Angles.Zero;
}
