namespace Facepunch;

public interface IViewModelOffset
{
	public Vector3 PositionOffset { get; }
	public Angles AngleOffset { get; }
}

/// <summary> One optic's sight line on a weapon: see <see cref="ManualOffset.OpticSightLines"/>. </summary>
public class OpticSightLine
{
	[KeyProperty] public Gunsmith.GunsmithPart Optic { get; set; }
	/// <summary> Added to the optic's aim offset: how far the eye moves, in the aimed gun's frame. </summary>
	public Vector3 Position { get; set; }
	/// <summary> Added to the optic's aim angles: how far the gun turns about the eye (pitch down, yaw left). </summary>
	public Angles Angles { get; set; }
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

	/// <summary>
	/// How far this weapon's ADS pose turns its optic rail off the line of sight. A 1x sight's reticle is collimated, so
	/// its dot shows where the sight points, and the gun turns this much about the eye (pitch down, yaw left) to put the
	/// dot on the screen's centre, where the shots go. Magnified sights learn their own alignment (OpticZoom) and don't
	/// take it. Measured per weapon in output/reticle-survey-*; the ported guns' come from Tools/kastov_prefabs.py.
	/// </summary>
	[Property] public Angles OpticAimAngleCorrection { get; set; }

	/// <summary> <see cref="OpticAimAngleCorrection"/> for a sight of this magnification. </summary>
	public Angles OpticAngleCorrection( float magnification ) => magnification <= 1f ? OpticAimAngleCorrection : Angles.Zero;

	/// <summary>
	/// Per optic, on top of <see cref="OpticAimCorrection"/>, for a weapon whose front sight post stays up under an optic
	/// (the M16A4's fixed front sight base). The eye moves and the gun turns a fraction of a degree, so the dot sits
	/// against the post as a real sight's does (on its tip at absolute co-witness, above it at lower 1/3) and on the
	/// screen's centre, where the shots go. The models aren't the real heights, so without it the dot sat low in the front
	/// sight. Measured with hc1_m16_cowitness.
	/// </summary>
	[Property] public List<OpticSightLine> OpticSightLines { get; set; }

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
			Player.AimDampening /= Equipment.GetOpticMagnification( optic );
		}
	}

	Vector3 IViewModelOffset.PositionOffset => IsAiming
		? Equipment.IsValid() && Equipment.TryGetOpticAim( out var optic )
			? Equipment.GetOpticAimOffset( optic ) + OpticAimCorrection + (SightLine( optic )?.Position ?? Vector3.Zero) + RailCorrection( true )
			: AimOffset + RailCorrection( false )
		: Vector3.Zero;
	private Vector3 RailCorrection( bool optic ) => Equipment.IsValid() && Equipment.ApplySavedAttachments
		&& Gunsmith.GunsmithLoadoutManager.TryGetAttachment( Equipment.Resource, Gunsmith.GunsmithPartType.Rail, out var rail )
		&& rail.IsValid() // a rail saved as "none" is found, with no part
		? optic ? rail.RailOpticAimCorrection : rail.RailIronAimCorrection : Vector3.Zero;
	Angles IViewModelOffset.AngleOffset => IsAiming
		? Equipment.IsValid() && Equipment.TryGetOpticAim( out var optic )
			? Equipment.GetOpticAimAngles( optic ) + OpticAngleCorrection( Equipment.GetOpticMagnification( optic ) )
				+ (SightLine( optic )?.Angles ?? Angles.Zero)
			: AimAngleOffset
		: Angles.Zero;

	private OpticSightLine SightLine( Gunsmith.GunsmithPart optic )
	{
		if ( OpticSightLines is null )
			return null;

		foreach ( var line in OpticSightLines )
		{
			if ( line is not null && line.Optic == optic )
				return line;
		}

		return null;
	}
}
