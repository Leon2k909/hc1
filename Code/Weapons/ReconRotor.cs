namespace Facepunch;

/// <summary>
/// One of a <see cref="ReconOctocopter"/>'s eight rotors. Slow, its blades show. Faster, a flat disc takes their place,
/// whose shader (<c>hc1_rotor_blur.shader</c>) works out what the eye sees: each point darkened by the share of the
/// time a blade covers it, from the blades' real chord, twist and sweep, seen edge-on or face-on. The blades leave a
/// fading trail while the eye can still follow them, and fuse into an even, faintly see-through disc once they pass a
/// point ~50 times a second (at 2,900 rpm they pass 97 times). The hub looks the same turning, so it's always drawn.
/// </summary>
public sealed class ReconRotor : Component
{
	/// <summary>+1 turns anticlockwise seen from above, -1 clockwise.</summary>
	[Property] public float Spin { get; set; } = 1f;
	[Property] public ModelRenderer Hub { get; set; }
	[Property] public ModelRenderer Blades { get; set; }
	[Property] public ModelRenderer Disc { get; set; }

	/// <summary>Above this the blades are drawn by the disc's shader.</summary>
	[Property] public float BlurRpm { get; set; } = 240f;

	/// <summary>How long the eye keeps what it saw: the trail behind a blade it can still follow.</summary>
	private const float Persistence = 0.025f;

	/// <summary>Blade passes a second over which the blades fuse into an even disc (two blades a turn).</summary>
	private const float FuseFrom = 20f, FuseAt = 50f;

	private float _angle;

	public void Turn( float rpm, float delta )
	{
		// rpm x 360 / 60 degrees a second.
		_angle = (_angle + Spin * rpm * 6f * delta) % 360f;
		LocalRotation = Rotation.FromYaw( _angle );

		var blurred = rpm >= BlurRpm;
		if ( Blades.IsValid() ) Blades.Enabled = !blurred;
		if ( !Disc.IsValid() ) return;
		Disc.Enabled = blurred;
		if ( !blurred ) return;

		Disc.Tint = Color.White;
		var scene = Disc.SceneObject;
		if ( !scene.IsValid() ) return;
		// The shader takes where the blades are from the disc itself, which turns with the rotor.
		var radians = rpm * MathF.PI / 30f;
		var passes = rpm / 30f;
		var fuse = Math.Clamp( (passes - FuseFrom) / (FuseAt - FuseFrom), 0f, 1f );
		scene.Attributes.Set( "RotorSpin", Spin >= 0f ? 1f : -1f );
		scene.Attributes.Set( "RotorTrail", radians * Persistence );
		scene.Attributes.Set( "RotorFusion", fuse * fuse * (3f - 2f * fuse) );
	}
}
