HEADER
{
	Description = "Restrained photographic response";
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
		o.vPositionPs = float4( i.vPositionOs.xy, 0, 1 );
		o.uv = i.vTexCoord;
		return o;
	}
}
PS
{
	#include "postprocess/common.hlsl"
	RenderState( BlendEnable, false );
	Texture2D g_tColorBuffer < Attribute( "ColorBuffer" ); SrgbRead( true ); >;
	float g_flStrength < Attribute( "PhotoStrength" ); Default( 0 ); >;
	float g_flContrast < Attribute( "PhotoContrast" ); Default( 0 ); >;
	float g_flHighlights < Attribute( "PhotoHighlights" ); Default( 0 ); >;
	float g_flSoftness < Attribute( "PhotoSoftness" ); Default( 0 ); >;
	float g_flAberration < Attribute( "PhotoAberration" ); Default( 0 ); >;
	float g_flGrain < Attribute( "PhotoGrain" ); Default( 0 ); >;

	float Luma( float3 c ) { return dot( c, float3( 0.2126, 0.7152, 0.0722 ) ); }
	float3 Sample( float2 uv ) { return g_tColorBuffer.SampleLevel( g_sBilinearClamp, uv, 0 ).rgb; }

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		float2 uv = CalculateViewportUv( i.vPositionSs.xy );
		float3 original = Sample( uv );
		float2 texel = g_vInvViewportSize.xy;
		float scale = g_vViewportSize.y / 1080.0;
		float2 radial = ( uv - 0.5 ) * 2.0;
		// The central half of the picture, including sights, has no lens separation or softness.
		float edge = smoothstep( 0.45, 1.2, length( radial ) );
		float2 separation = radial * edge * g_flAberration * texel * scale;
		float3 color = float3( Sample( uv + separation ).r, original.g, Sample( uv - separation ).b );

		float2 nearStep = texel * scale;
		float3 nearMean = ( Sample( uv + float2( nearStep.x, 0 ) ) + Sample( uv - float2( nearStep.x, 0 ) )
			+ Sample( uv + float2( 0, nearStep.y ) ) + Sample( uv - float2( 0, nearStep.y ) ) ) * 0.25;
		color = lerp( color, nearMean, edge * g_flSoftness );

		// Bounded, luminance-only local contrast. Suppress it at deep shadows and hard silhouettes.
		float2 broadStep = texel * scale * 10;
		float mean = ( Luma( Sample( uv + float2( broadStep.x, 0 ) ) ) + Luma( Sample( uv - float2( broadStep.x, 0 ) ) )
			+ Luma( Sample( uv + float2( 0, broadStep.y ) ) ) + Luma( Sample( uv - float2( 0, broadStep.y ) ) ) ) * 0.25;
		float lum = Luma( color );
		float delta = lum - mean;
		float guard = smoothstep( 0.008, 0.06, lum ) * ( 1.0 - smoothstep( 0.08, 0.25, abs( delta ) ) );
		float targetLum = max( 0, lum + clamp( delta, -0.025, 0.025 ) * g_flContrast * guard );
		color *= targetLum / max( lum, 0.00001 );
		color = lerp( color, Luma( color ).xxx, smoothstep( 0.45, 0.95, lum ) * g_flHighlights );

		// Zero-mean monochrome sensor noise in perceptual space; neither crushed blacks nor bright sky is filled in.
		float noise = frac( 52.9829189 * frac( dot( i.vPositionSs.xy + floor( g_flTime * 60.0 ) * float2( 17, 29 ), float2( 0.06711056, 0.00583715 ) ) ) ) - 0.5;
		float3 perceptual = sqrt( max( color, 0 ) );
		float grainMask = smoothstep( 0.001, 0.025, lum ) * ( 1.0 - smoothstep( 0.4, 1.0, lum ) );
		perceptual = max( 0, perceptual + noise * g_flGrain * grainMask );
		color = perceptual * perceptual;
		return float4( lerp( original, color, g_flStrength ), 1 );
	}
}
