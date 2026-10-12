namespace Facepunch;

/// <summary>
/// One of a <see cref="ReconOctocopter"/>'s eight rotors. Slow, its blades show. Faster, a flat disc takes their place,
/// whose shader (<c>hc1_rotor_blur.shader</c>) works out what the eye sees: each point darkened by the share of the
/// time a blade covers it, from the blades' real chord, twist and sweep, seen edge-on or face-on. The blades leave a
/// fading trail while the eye can still follow them, and fuse into an even, faintly see-through disc once they pass a
/// point ~50 times a second (at 2,900 rpm they pass 97 times). The hub looks the same turning, so it's always drawn.
/// <para>
/// The nano drone's main and tail rotors (<see cref="ReconOctocopter"/> flies it too) are the octocopter's blade
/// scaled down: <see cref="ShaderScale"/> tells the shader by how much, and they have no yoke.
/// </para>
/// </summary>
public sealed class ReconRotor : Component
{
	/// <summary>+1 turns anticlockwise seen from above (from the rotor's +z), -1 clockwise.</summary>
	[Property] public float Spin { get; set; } = 1f;
	[Property] public ModelRenderer Hub { get; set; }
	[Property] public ModelRenderer Blades { get; set; }
	[Property] public ModelRenderer Disc { get; set; }

	/// <summary>Above this the blades are drawn by the disc's shader.</summary>
	[Property] public float BlurRpm { get; set; } = 240f;

	/// <summary>This rotor's speed over the drone's rotor speed: a tail rotor turns faster than the main one.</summary>
	[Property] public float RpmScale { get; set; } = 1f;

	/// <summary>The octocopter's prop radius over this rotor's (the shader's <c>RotorScale</c>).</summary>
	[Property] public float ShaderScale { get; set; } = 1f;

	/// <summary>Whether the blades fold on a yoke the shader draws (the octocopter's do).</summary>
	[Property] public bool Yoke { get; set; } = true;

	/// <summary>How long the eye keeps what it saw: the trail behind a blade it can still follow.</summary>
	private const float Persistence = 0.025f;

	/// <summary>Blade passes a second over which the blades fuse into an even disc (two blades a turn).</summary>
	private const float FuseFrom = 20f, FuseAt = 50f;

	private float _angle;

	public void Turn( float rpm, float delta )
	{
		rpm *= RpmScale;
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
		scene.Attributes.Set( "RotorScale", ShaderScale );
		scene.Attributes.Set( "RotorYoke", Yoke ? 1f : 0f );
	}
}
