HEADER
{
	Description = "HC1 object-projected animated camo";
	DevShader = true;
}

MODES
{
	Forward();
	Depth();
}

FEATURES
{
	#include "common/features.hlsl"

	Feature( F_SELF_ILLUM, 0..1, "Self Illumination" );
}

COMMON
{
	#define S_SPECULAR 1
	#include "common/shared.hlsl"
}

struct VertexInput
{
	#include "common/vertexinput.hlsl"
};

struct PixelInput
{
	#include "common/pixelinput.hlsl"

	float3 vPositionOs : TEXCOORD8;
	float3 vNormalOs : TEXCOORD9;
};

VS
{
	#include "common/vertex.hlsl"

	PixelInput MainVs( VertexInput i )
	{
		PixelInput o = ProcessVertex( i );

		float3 vNormalOs;
		float4 vTangentUOs_flTangentVSign;
		VS_DecodeObjectSpaceNormalAndTangent( i, vNormalOs, vTangentUOs_flTangentVSign );

		o.vPositionOs = i.vPositionOs.xyz;
		o.vNormalOs = vNormalOs;

		return FinalizeVertex( o );
	}
}

PS
{
	#include "common/pixel.hlsl"

	StaticCombo( S_SELF_ILLUM, F_SELF_ILLUM, Sys( ALL ) );

	CreateInputTexture2D( TextureColor, Srgb, 8, "", "_color", "Camo,10/10", Default3( 1.0, 1.0, 1.0 ) );
	Texture2D g_tColor < Channel( RGB, Box( TextureColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;

	TextureAttribute( LightSim_DiffuseAlbedoTexture, g_tColor );
	TextureAttribute( RepresentativeTexture, g_tColor );

	SamplerState g_sCamoSampler < Filter( ANISO ); AddressU( WRAP ); AddressV( WRAP ); >;

	float2 g_vTexCoordScale < UiType( Slider ); Default2( 1.0, 1.0 ); Range2( 0.05, 0.05, 8.0, 8.0 ); UiGroup( "Camo,10/20" ); >;
	float2 g_vTexCoordScrollSpeed < UiType( Slider ); Default2( -0.025, -0.040 ); Range2( -2.0, -2.0, 2.0, 2.0 ); UiGroup( "Camo,10/30" ); >;
	float g_flCamoProjectionScale < UiType( Slider ); Default( 0.125 ); Range( 0.01, 0.50 ); UiGroup( "Camo,10/40" ); >;
	float g_flTriplanarSharpness < UiType( Slider ); Default( 4.0 ); Range( 1.0, 12.0 ); UiGroup( "Camo,10/50" ); >;

	float g_flModelTintAmount < UiType( Slider ); Default( 1.0 ); Range( 0.0, 1.0 ); UiGroup( "Tint,20/10" ); >;
	float4 g_vColorTint < UiType( Color ); Default4( 1.0, 1.0, 1.0, 0.0 ); UiGroup( "Tint,20/20" ); >;

	float g_flRoughness < UiType( Slider ); Default( 0.42 ); Range( 0.02, 1.0 ); UiGroup( "Surface,30/10" ); >;
	float g_flMetalness < UiType( Slider ); Default( 0.0 ); Range( 0.0, 1.0 ); UiGroup( "Surface,30/20" ); >;
	float g_flAmbientOcclusion < UiType( Slider ); Default( 1.0 ); Range( 0.0, 1.0 ); UiGroup( "Surface,30/30" ); >;

	#if S_SELF_ILLUM
		CreateInputTexture2D( TextureSelfIllumMask, Srgb, 8, "", "_selfillum", "Self Illum,40/10", Default3( 1.0, 1.0, 1.0 ) );
		Texture2D g_tSelfIllumMask < Channel( RGB, Box( TextureSelfIllumMask ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;

		float g_flSelfIllumAlbedoFactor < UiType( Slider ); Default( 1.0 ); Range( 0.0, 1.0 ); UiGroup( "Self Illum,40/20" ); >;
		float g_flSelfIllumBrightness < UiType( Slider ); Default( 2.0 ); Range( 0.0, 10.0 ); UiGroup( "Self Illum,40/30" ); >;
		float g_flSelfIllumScale < UiType( Slider ); Default( 1.0 ); Range( 0.0, 8.0 ); UiGroup( "Self Illum,40/40" ); >;
		float2 g_vSelfIllumScrollSpeed < UiType( Slider ); Default2( -0.025, -0.040 ); Range2( -2.0, -2.0, 2.0, 2.0 ); UiGroup( "Self Illum,40/50" ); >;
		float4 g_vSelfIllumTint < UiType( Color ); Default4( 1.0, 1.0, 1.0, 0.0 ); UiGroup( "Self Illum,40/60" ); >;
	#endif

	float3 GetTriplanarBlend( float3 normalOs )
	{
		float3 blend = pow( abs( normalize( normalOs ) ), g_flTriplanarSharpness );
		float total = max( blend.x + blend.y + blend.z, 0.0001 );
		return blend / total;
	}

	float3 GetProjectedPosition( float3 positionOs )
	{
		return positionOs * g_flCamoProjectionScale;
	}

	float3 GetProjectedFlow( float2 scrollSpeed )
	{
		return float3( scrollSpeed.x, scrollSpeed.y, scrollSpeed.x ) * g_flTime;
	}

	float3 SampleProjectedCamo( float3 positionOs, float3 normalOs, float2 scrollSpeed )
	{
		float3 p = GetProjectedPosition( positionOs );
		float3 flow = GetProjectedFlow( scrollSpeed );
		float3 blend = GetTriplanarBlend( normalOs );

		// Apply flow in 3D space BEFORE extracting 2D planes to ensure perfectly seamless blending
		float3 animatedPos = p + flow;

		float2 uvX = animatedPos.yz * g_vTexCoordScale;
		float2 uvY = animatedPos.xz * g_vTexCoordScale;
		float2 uvZ = animatedPos.xy * g_vTexCoordScale;

		float3 x = g_tColor.Sample( g_sCamoSampler, uvX ).rgb;
		float3 y = g_tColor.Sample( g_sCamoSampler, uvY ).rgb;
		float3 z = g_tColor.Sample( g_sCamoSampler, uvZ ).rgb;

		return x * blend.x + y * blend.y + z * blend.z;
	}

	#if S_SELF_ILLUM
		float3 SampleProjectedSelfIllum( float3 positionOs, float3 normalOs )
		{
			float3 p = GetProjectedPosition( positionOs );
			float3 flow = GetProjectedFlow( g_vSelfIllumScrollSpeed );
			float3 blend = GetTriplanarBlend( normalOs );

			// Apply flow in 3D space BEFORE extracting 2D planes to ensure perfectly seamless blending
			float3 animatedPos = p + flow;

			float2 uvX = animatedPos.yz * g_vTexCoordScale;
			float2 uvY = animatedPos.xz * g_vTexCoordScale;
			float2 uvZ = animatedPos.xy * g_vTexCoordScale;

			float3 x = g_tSelfIllumMask.Sample( g_sCamoSampler, uvX ).rgb;
			float3 y = g_tSelfIllumMask.Sample( g_sCamoSampler, uvY ).rgb;
			float3 z = g_tSelfIllumMask.Sample( g_sCamoSampler, uvZ ).rgb;

			return x * blend.x + y * blend.y + z * blend.z;
		}
	#endif

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		Material m = Material::Init( i );

		float3 camo = SampleProjectedCamo( i.vPositionOs, i.vNormalOs, g_vTexCoordScrollSpeed );
		float3 tint = lerp( float3( 1.0, 1.0, 1.0 ), g_vColorTint.rgb, g_flModelTintAmount );

		m.Albedo = camo * tint * i.vVertexColor.rgb;
		m.Normal = normalize( i.vNormalWs );
		m.Roughness = g_flRoughness;
		m.Metalness = g_flMetalness;
		m.AmbientOcclusion = g_flAmbientOcclusion;
		m.Opacity = 1.0;

		#if S_SELF_ILLUM
			float3 selfIllum = SampleProjectedSelfIllum( i.vPositionOs, i.vNormalOs ) * g_vSelfIllumTint.rgb * g_flSelfIllumBrightness * g_flSelfIllumScale;
			m.Albedo = lerp( m.Albedo, max( m.Albedo, selfIllum ), g_flSelfIllumAlbedoFactor );
			m.Emission += selfIllum;
		#endif

		return ShadingModelStandard::Shade( i, m );
	}
}
