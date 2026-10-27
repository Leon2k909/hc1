using Sandbox.Rendering;

namespace Facepunch;

/// <summary>A restrained photographic finish after the map's exposure and tone mapping.</summary>
[Title( "Photographic Response" ), Category( "Post Processing" ), Icon( "photo_camera" )]
public sealed class PhotographicResponse : BasePostProcess<PhotographicResponse>
{
	[Property, Range( 0, 1 )] public float Strength { get; set; } = 0.65f;
	[Property, Range( 0, 0.4f )] public float LocalContrast { get; set; } = 0.15f;
	[Property, Range( 0, 0.4f )] public float HighlightDesaturation { get; set; } = 0.12f;
	[Property, Range( 0, 0.5f )] public float EdgeSoftness { get; set; } = 0.18f;
	/// <summary>Maximum radial colour separation, in pixels at 1080p. Zero in the aiming region.</summary>
	[Property, Range( 0, 1 )] public float Aberration { get; set; } = 0.3f;
	[Property, Range( 0, 0.05f )] public float Grain { get; set; } = 0.012f;

	private static Material ResponseMaterial => Material.FromShader( "shaders/hc1_photographic_response.shader" );

	public override void Render()
	{
		var strength = GetWeighted( static x => x.Strength, 0f ).Clamp( 0f, 1f );
		if ( strength <= 0f ) return;

		Attributes.Set( "PhotoStrength", strength );
		Attributes.Set( "PhotoContrast", GetWeighted( static x => x.LocalContrast, 0f ).Clamp( 0f, 0.4f ) );
		Attributes.Set( "PhotoHighlights", GetWeighted( static x => x.HighlightDesaturation, 0f ).Clamp( 0f, 0.4f ) );
		Attributes.Set( "PhotoSoftness", GetWeighted( static x => x.EdgeSoftness, 0f ).Clamp( 0f, 0.5f ) );
		Attributes.Set( "PhotoAberration", GetWeighted( static x => x.Aberration, 0f ).Clamp( 0f, 1f ) );
		Attributes.Set( "PhotoGrain", GetWeighted( static x => x.Grain, 0f ).Clamp( 0f, 0.05f ) );
		// The HUD and flashbang overlay render later. No depth, history or mip chain is allocated.
		Blit( BlitMode.WithBackbuffer( ResponseMaterial, Stage.AfterPostProcess, 1000, false ), "Photographic Response" );
	}
}
