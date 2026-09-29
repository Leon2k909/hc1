//
// A flashbang's afterimage and blur (Code/Utils/FlashbangEffect.cs).
//
// FlashMode 1 copies the frame, at half size, into the afterimage texture the moment the flash goes off. Every frame
// after that, FlashMode 0 lays the afterimage over the view. The retina keeps a picture of what it saw by the flash's
// light, so the afterimage is that frame as the flash lit it: much brighter (the darkest corners least), paler and
// softer. It's screened onto the live view, since a positive afterimage adds to what you see rather than hiding it, so
// the dark parts of the room show the view underneath.
//
// Where the flash itself was in view, its image burns a spot into the retina: bright at first, then a dim purplish blot
// (the negative afterimage) that outlasts the rest. Both stay where they are on screen when you turn, as an afterimage
// does.
//
// Flash blindness also takes the eyes' sharpness, and the blast's daze stops them focusing, so the view underneath is
// blurred (FlashBlur): 17 taps over a disc, each read from the frame's mip chain at a level about a third of the disc's
// radius across, so neighbouring taps overlap and together they're smooth.
//
HEADER
{
	Description = "Flashbang afterimage";
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

	Texture2D g_tColorBuffer < Attribute( "ColorBuffer" ); SrgbRead( true ); >;
	Texture2D g_tAfterimage < Attribute( "FlashAfterimage" ); SrgbRead( false ); >;

	float g_flMode < Attribute( "FlashMode" ); Default( 0.0f ); >;
	float2 g_vTargetSize < Attribute( "FlashTargetSize" ); Default2( 1.0f, 1.0f ); >;
	float2 g_vAfterimageTexel < Attribute( "FlashAfterimageTexel" ); Default2( 0.001f, 0.001f ); >;
	float g_flAfterimage < Attribute( "FlashAfterimageAlpha" ); Default( 0.0f ); >;
	float g_flGain < Attribute( "FlashGain" ); Default( 1.0f ); >;
	float g_flDesaturate < Attribute( "FlashDesaturate" ); Default( 0.0f ); >;
	float4 g_vSpot < Attribute( "FlashSpot" ); Default4( 0.5f, 0.5f, 0.0f, 1.0f ); >;
	float g_flSpotBright < Attribute( "FlashSpotBright" ); Default( 0.0f ); >;
	float g_flSpotDark < Attribute( "FlashSpotDark" ); Default( 0.0f ); >;

	// The blur: its disc's radius across and down (in uv), and the mip level each tap reads. Off when x is 0.
	float4 g_vBlur < Attribute( "FlashBlur" ); Default4( 0.0f, 0.0f, 0.0f, 0.0f ); >;

	// The blur's taps round the middle one: the engine's 16-tap Poisson disc (Shadows/ShadowFiltering.hlsl).
	static const float2 g_vBlurTaps[16] =
	{
		float2( -0.942016, -0.399062 ),
		float2( -0.094184, -0.938988 ),
		float2(  0.310720, -0.371712 ),
		float2( -0.545396, -0.589939 ),
		float2(  0.140388, -0.040836 ),
		float2(  0.667325,  0.174626 ),
		float2( -0.527440,  0.056346 ),
		float2(  0.346120, -0.935218 ),
		float2( -0.267592,  0.406868 ),
		float2( -0.850940,  0.424726 ),
		float2(  0.206578,  0.570748 ),
		float2( -0.413360,  0.855142 ),
		float2(  0.654718, -0.521624 ),
		float2(  0.954892,  0.016536 ),
		float2(  0.439138,  0.898128 ),
		float2(  0.878554, -0.397416 ),
	};

	float3 Screen( float3 a, float3 b )
	{
		return 1.0f - ( 1.0f - a ) * ( 1.0f - b );
	}

	float3 Blurred( float2 uv )
	{
		float3 sum = g_tColorBuffer.SampleLevel( g_sTrilinearClamp, uv, g_vBlur.z ).rgb;

		[unroll]
		for ( int k = 0; k < 16; k++ )
		{
			sum += g_tColorBuffer.SampleLevel( g_sTrilinearClamp, uv + g_vBlurTaps[k] * g_vBlur.xy, g_vBlur.z ).rgb;
		}

		return sum / 17.0f;
	}

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		// The copy: each half-size pixel's bilinear sample falls between the 2x2 pixels it covers, so it averages them.
		if ( g_flMode > 0.5f )
		{
			float2 copyUv = i.vPositionSs.xy / g_vTargetSize;
			return float4( g_tColorBuffer.SampleLevel( g_sBilinearClamp, copyUv, 0 ).rgb, 1.0f );
		}

		float2 uv = CalculateViewportUv( i.vPositionSs.xy );
		float3 color;

		[branch]
		if ( g_vBlur.x > 0.0f )
		{
			color = Blurred( uv );
		}
		else
		{
			color = g_tColorBuffer.SampleLevel( g_sBilinearClamp, uv, 0 ).rgb;
		}

		// A retina's picture isn't sharp.
		float2 t = g_vAfterimageTexel * 1.5f;
		float3 after = g_tAfterimage.SampleLevel( g_sBilinearClamp, uv, 0 ).rgb * 0.4f;
		after += g_tAfterimage.SampleLevel( g_sBilinearClamp, uv + float2( t.x, 0.0f ), 0 ).rgb * 0.15f;
		after += g_tAfterimage.SampleLevel( g_sBilinearClamp, uv - float2( t.x, 0.0f ), 0 ).rgb * 0.15f;
		after += g_tAfterimage.SampleLevel( g_sBilinearClamp, uv + float2( 0.0f, t.y ), 0 ).rgb * 0.15f;
		after += g_tAfterimage.SampleLevel( g_sBilinearClamp, uv - float2( 0.0f, t.y ), 0 ).rgb * 0.15f;

		// As the flash lit it.
		float3 lit = 1.0f - pow( saturate( 1.0f - after ), g_flGain );
		float luma = dot( lit, float3( 0.2126f, 0.7152f, 0.0722f ) );
		lit = lerp( lit, luma.xxx, g_flDesaturate );

		color = Screen( color, lit * g_flAfterimage );

		// The flash's own image, measured in screen widths: w is the screen's height over its width.
		float2 d = ( uv - g_vSpot.xy ) * float2( 1.0f, g_vSpot.w );
		float spot = exp( -dot( d, d ) / max( g_vSpot.z * g_vSpot.z, 1e-8f ) ) * step( 1e-5f, g_vSpot.z );
		color = Screen( color, spot * g_flSpotBright * float3( 1.0f, 0.97f, 0.88f ) );
		color *= 1.0f - spot * g_flSpotDark * float3( 0.55f, 0.75f, 0.5f );

		return float4( color, 1.0f );
	}
}
