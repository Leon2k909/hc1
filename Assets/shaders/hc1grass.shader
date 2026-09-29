//=========================================================================================================================
// HC1 grass: the engine's foliage shading (wrap lighting, backlight through the blades) on geometry blades that sway in
// a breeze of their own and sink into the ground towards the edge of the scattered area, so there's no line where the
// grass stops. A layer further out (the far grass) also rises out of the ground where the one before it sinks. Made for
// the clutter on Ridgeback's terrain (Tools/ridgeback_grass.py builds the models).
//
// The models stand on their origin with the blades going up +Z, so a vertex's height is how far along its blade it is:
// the sway bends tips and leaves roots. The engine's own foliage wind (g_vWindDirection) isn't set by anything in the
// game, which is why this doesn't use it.
//=========================================================================================================================
HEADER
{
	Description = "HC1 grass: foliage shading, its own breeze, sinks into the ground with distance";
}

FEATURES
{
	#include "common/features.hlsl"
	Feature( F_TRANSMISSIVE, 0..1, "Rendering" );
}

MODES
{
	Forward();
	Depth( S_MODE_DEPTH );
	ToolsShadingComplexity( "tools_shading_complexity.shader" );
}

COMMON
{
	#include "common/shared.hlsl"

	// Clumps sink into the ground between these distances from the camera (the vertex shader), and shade towards the
	// ground's own colour on the way there (the pixel shader)
	float g_flFadeStart < Default( 1000.0 ); Range( 0.0, 50000.0 ); UiGroup( "Grass,20/Distance" ); >;
	float g_flFadeEnd < Default( 1450.0 ); Range( 0.0, 50000.0 ); UiGroup( "Grass,20/Distance" ); >;
}

struct VertexInput
{
	#include "common/vertexinput.hlsl"
};

struct PixelInput
{
	#include "common/pixelinput.hlsl"
};

//=========================================================================================================================

VS
{
	#include "common/vertex.hlsl"

	float g_flBladeHeight < Default( 24.0 ); Range( 1.0, 200.0 ); UiGroup( "Grass,10/Sway" ); >;
	float g_flSwayAmount < Default( 1.2 ); Range( 0.0, 20.0 ); UiGroup( "Grass,10/Sway" ); >;
	float g_flSwaySpeed < Default( 0.9 ); Range( 0.0, 10.0 ); UiGroup( "Grass,10/Sway" ); >;
	float g_flGustAmount < Default( 3.0 ); Range( 0.0, 30.0 ); UiGroup( "Grass,10/Sway" ); >;
	float g_flGustLength < Default( 1400.0 ); Range( 50.0, 20000.0 ); UiGroup( "Grass,10/Sway" ); >;
	float g_flGustSpeed < Default( 260.0 ); Range( 0.0, 5000.0 ); UiGroup( "Grass,10/Sway" ); >;
	float2 g_vWindHeading < Default2( 0.6, -0.8 ); UiGroup( "Grass,10/Sway" ); >;

	// Up out of the ground between these distances from the camera, for a layer taking over from a nearer one as it
	// sinks. Both 0: no rise.
	float g_flRiseStart < Default( 0.0 ); Range( 0.0, 50000.0 ); UiGroup( "Grass,20/Distance" ); >;
	float g_flRiseEnd < Default( 0.0 ); Range( 0.0, 50000.0 ); UiGroup( "Grass,20/Distance" ); >;

	PixelInput MainVs( VertexInput i )
	{
		PixelInput o = ProcessVertex( i );

		float3x4 matObjectToWorld = GetTransformMatrix( i.nInstanceTransformID );
		float3 vOriginWs = mul( matObjectToWorld, float4( 0, 0, 0, 1 ) );

		// Down into the ground as it nears the edge of the scattered tiles round the camera
		float flDistance = length( vOriginWs.xy - g_vCameraPositionWs.xy );
		float flGrow = 1.0 - smoothstep( g_flFadeStart, g_flFadeEnd, flDistance );
		flGrow *= g_flRiseEnd > 0.0 ? smoothstep( g_flRiseStart, g_flRiseEnd, flDistance ) : 1.0;

		// All the way down, the clump folds up to its root as well, so it draws nothing: flattened, it would still show
		// where it overhangs the downhill side of a slope
		float flSpread = saturate( flGrow * 5.0 );
		float3 vPositionOs = i.vPositionOs.xyz * float3( flSpread, flSpread, flGrow );

		// How far up its blade the vertex is: roots stay put, tips move most
		float flBend = pow( saturate( i.vPositionOs.z / g_flBladeHeight ), 1.6 );

		// Gusts roll across the field downwind; each clump and blade flutters on its own phase as well
		float2 vHeading = normalize( g_vWindHeading );
		float flAlong = dot( vOriginWs.xy, vHeading );
		float flGust = 0.5 + 0.5 * sin( ( flAlong - g_flTime * g_flGustSpeed ) * ( 6.2831853 / g_flGustLength ) );
		flGust *= flGust;
		float flPhase = dot( vOriginWs.xy, float2( 0.0131, 0.0173 ) ) + dot( i.vPositionOs.xy, float2( 0.37, 0.23 ) );
		float flTime = g_flTime * g_flSwaySpeed * 6.2831853;
		float flFlutter = sin( flTime + flPhase ) + 0.4 * sin( flTime * 2.37 + flPhase * 1.7 );
		float2 vCross = float2( -vHeading.y, vHeading.x ) * 0.35 * sin( flTime * 0.83 + flPhase * 1.3 );

		float flPush = ( g_flGustAmount * flGust + g_flSwayAmount * flFlutter ) * flBend * flGrow;
		o.vPositionWs = mul( matObjectToWorld, float4( vPositionOs, 1.0 ) );
		o.vPositionWs.xy += ( vHeading + vCross ) * flPush;
		o.vPositionWs.z -= 0.3 * abs( flPush ) * flBend;           // a bent blade doesn't reach as high
		o.vPositionPs.xyzw = Position3WsToPs( o.vPositionWs.xyz );

		return FinalizeVertex( o );
	}
}

//=========================================================================================================================

PS
{
	#include "common/utils/Material.CommonInputs.hlsl"
	#include "common/pixel.hlsl"
	#include "common/classes/Light.hlsl"

	StaticCombo( S_TRANSMISSIVE, F_TRANSMISSIVE, Sys( ALL ) );

	RenderState( CullMode, F_RENDER_BACKFACES ? NONE : DEFAULT );

	#if ( S_MODE_DEPTH == 0 )
		RenderState( DepthFunc, EQUAL );
		RenderState( DepthWriteEnable, false );
	#endif

	float g_flWrapAmount < Default( 0.5 ); Range( 0.0, 1.0 ); UiGroup( "Foliage" ); >;
	float g_flWrapStrength < Default( 0.3 ); Range( 0.0, 1.0 ); UiGroup( "Foliage" ); >;
	float g_flMinRoughness < Default( 0.6 ); Range( 0.0, 1.0 ); UiGroup( "Foliage" ); >;
	float g_flGrassNormalUp < Default( 0.6 ); Range( 0.0, 1.0 ); UiGroup( "Foliage" ); >;
	float g_flColourVariation < Default( 0.12 ); Range( 0.0, 1.0 ); UiGroup( "Foliage" ); >;
	float3 g_vFarTint < Default3( 0.70, 0.64, 0.72 ); UiGroup( "Grass,20/Distance" ); >;

	#if S_TRANSMISSIVE
		CreateInputTexture2D( TextureTransmissiveColor, Srgb, 8, "", "_color", "Material,10/60", Default3( 1.0, 1.0, 1.0 ) );
		Texture2D g_tTransmissiveColor < Channel( RGB, Box( TextureTransmissiveColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
		float g_flTransmissionScale < Default( 0.6 ); Range( 0.0, 10.0 ); UiGroup( "Transmissive" ); >;
	#endif

	// Wrap diffuse and back-scatter for the sun, as foliage.shader does it (added as emission on top of Shade()).
	void ApplySunScatter( inout Material m, float3 viewDir, float3 transmissionTint )
	{
		if ( !g_DirectionalLightEnabled )
			return;

		float3 lightDir = -normalize( g_DirectionalLightDirection.xyz );
		float3 lightColor = g_DirectionalLightColor.rgb;
		float visibility = DirectionalLightShadow::GetVisibility( m.WorldPosition, m.ScreenPosition );

		if ( g_flWrapStrength > 0.0 )
		{
			float NdotL = dot( m.Normal, lightDir );
			float wrapped = saturate( ( NdotL + g_flWrapAmount ) / ( 1.0 + g_flWrapAmount ) );
			m.Emission += m.Albedo * lightColor * max( wrapped - saturate( NdotL ), 0.0 ) * g_flWrapStrength;
		}

		#if S_TRANSMISSIVE
			float3 scatterDir = normalize( lightDir + m.Normal * 0.2 );
			float backlit = pow( saturate( dot( viewDir, -scatterDir ) ), 3.0 );
			m.Emission += m.Albedo * transmissionTint * lightColor * ( backlit + 0.1 ) * lerp( 0.2, 1.0, visibility ) * g_flTransmissionScale;
		#endif
	}

	#if ( S_MODE_DEPTH == 0 )
		[earlydepthstencil]
	#endif
	float4 MainPs( PixelInput i ) : SV_Target0
	{
		Material m = Material::From( i );

		m.Roughness = max( m.Roughness, g_flMinRoughness );

		// Blades lit more like the ground they stand on than like thin cards facing every way
		m.Normal = normalize( lerp( m.Normal, float3( 0, 0, 1 ), g_flGrassNormalUp ) );

		// Broad patches of lusher and paler grass, so the field isn't one colour
		float2 p = m.WorldPosition.xy;
		float patches = sin( p.x * 0.0021 + sin( p.y * 0.0013 ) * 2.1 ) * sin( p.y * 0.0017 + sin( p.x * 0.0011 ) * 1.7 );
		m.Albedo *= 1.0 + g_flColourVariation * float3( patches * 0.6, patches * 0.25, -patches * 0.2 );

		// Towards the fade the blades take on the ground's shade (g_vFarTint is the ground's colour over the blades'),
		// so the field doesn't end in a brighter band where the clumps sink away
		float flFar = smoothstep( g_flFadeStart * 0.3, g_flFadeEnd, length( m.WorldPosition.xy - g_vCameraPositionWs.xy ) );
		m.Albedo *= lerp( float3( 1.0, 1.0, 1.0 ), g_vFarTint, flFar );

		float3 viewDir = normalize( g_vCameraPositionWs - m.WorldPosition );

		#if S_TRANSMISSIVE
			float3 transmissiveColor = g_tTransmissiveColor.Sample( TextureFiltering, i.vTextureCoords.xy ).rgb * ( 1.0 - 0.6 * flFar );
		#else
			float3 transmissiveColor = 1.0;
		#endif

		ApplySunScatter( m, viewDir, transmissiveColor );

		return ShadingModelStandard::Shade( i, m );
	}
}
