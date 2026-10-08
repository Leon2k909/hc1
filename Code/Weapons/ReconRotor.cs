namespace Facepunch;

/// <summary>
/// One of a <see cref="ReconOctocopter"/>'s eight rotors. Slow, its blades show; fast, they blur into a disc, as a
/// camera sees them (at 2,900 rpm a two-blade prop turns ~290 degrees a frame at 60 fps).
/// </summary>
public sealed class ReconRotor : Component
{
	/// <summary>+1 turns anticlockwise seen from above, -1 clockwise.</summary>
	[Property] public float Spin { get; set; } = 1f;
	[Property] public ModelRenderer Blades { get; set; }
	[Property] public ModelRenderer Disc { get; set; }

	/// <summary>Above this the blades are only the disc.</summary>
	[Property] public float BlurRpm { get; set; } = 900f;

	private float _angle;

	public void Turn( float rpm, float delta )
	{
		// rpm x 360 / 60 degrees a second.
		_angle = (_angle + Spin * rpm * 6f * delta) % 360f;
		LocalRotation = Rotation.FromYaw( _angle );

		if ( Blades.IsValid() ) Blades.Enabled = rpm < BlurRpm;
		if ( !Disc.IsValid() ) return;
		var blur = Math.Clamp( (rpm - 200f) / 1300f, 0f, 1f );
		Disc.Enabled = blur > 0.01f;
		Disc.Tint = Color.White.WithAlpha( blur * blur * (3f - 2f * blur) * 0.55f );
	}
}
