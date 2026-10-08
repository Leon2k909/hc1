//
// The HUD markers' mask (Code/UI/MarkerSystem/ViewModelMask.cs): white where the first-person gun leaves the view
// open, black where it covers it.
//
// GunDepth is a depth target that only the viewmodel has been drawn into, with its own materials. Surfaces that write
// depth (the gun, the arms, the parts) cover the view. Reticles and lens glass blend without writing depth
// (m4_optic_lens.shader), so the view through a red dot's window stays open, and so do see-through magazines.
//
HEADER
{
	Description = "HUD marker mask from the viewmodel's depth";
	DevShader = true;
}

MODES
{
	Default();
	Forward();
}

COMMON
{
	#include "postprocess/shared.hlsl"
}

struct VertexInput
{
	float3 vPositionOs : POSITION < Semantic( PosXyz ); >;
	float2 vTexCoord : TEXCOORD0 < Semantic( LowPrecisionUv ); >;
};

struct PixelInput
{
	float2 uv : TEXCOORD0;

	#if ( PROGRAM == VFX_PROGRAM_VS )
		float4 vPositionPs : SV_Position;
	#endif

	#if ( PROGRAM == VFX_PROGRAM_PS )
		float4 vPositionSs : SV_Position;
	#endif
};

VS
{
	PixelInput MainVs( VertexInput i )
	{
		PixelInput o;
		o.vPositionPs = float4( i.vPositionOs.xy, 0.0f, 1.0f );
		o.uv = i.vTexCoord;
		return o;
	}
}

PS
{
	#include "postprocess/common.hlsl"

	RenderState( BlendEnable, false );

	Texture2D g_tGunDepth < Attribute( "GunDepth" ); SrgbRead( false ); >;
	float4 g_vScopeLens < Attribute( "ScopeLens" ); Default4( 0.0f, 0.0f, 0.0f, 0.0f ); >;

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		// The mask and the depth target are the same size, so this pixel is the same one in both.
		float depth = g_tGunDepth.Load( int3( i.vPositionSs.xy, 0 ) ).r;

		// Nothing was drawn where the depth is still cleared: 0 with reversed depth, 1 without.
		float open = ( depth <= 0.0f || depth >= 1.0f ) ? 1.0f : 0.0f;

		// The lens has its own projected markers. Fade out the main view's markers beneath its picture.
		float lens = 1.0f - smoothstep( g_vScopeLens.z - 1.0f, g_vScopeLens.z, length( i.vPositionSs.xy - g_vScopeLens.xy ) );
		open *= 1.0f - lens * g_vScopeLens.w;

		// In the alpha too, so the mask works as a luminance or an alpha mask.
		return float4( open, open, open, open );
	}
}
