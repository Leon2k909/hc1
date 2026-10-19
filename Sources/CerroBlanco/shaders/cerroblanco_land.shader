//=========================================================================================================================
// Cerro Blanco's land: the hill round the museum and the sierra beyond it (Tools/cerroblanco_landscape.py), in four of
// the terrain's drawn ground materials (dry meadow, green meadow, dirt, limestone) blended by a painted splat.
//
// The splat (red green, green dirt, blue rock, the rest dry meadow; alpha the land's broad light and dark) spans the
// landscape's grid: along each axis its texels follow the grid's spacing, finest by the play (g_vSpacing.x out to
// g_vZones.x from the play's rectangle), then g_vSpacing.y out to g_vZones.y and g_vSpacing.z out to g_vZones.z, so a texel
// stays about the same size on screen wherever it's seen from the play. Rows run south. The mesh needs no UVs.
//
// Each material is sampled in plan at its real size (g_flTile), and again at a coarser scale further off so the ground
// doesn't repeat. They're blended by their own heights (the alpha of their colour), so dry grass gives way to bare earth
// round its tufts and stones stand out of the grass, rather than one fading through the other. Normals are DirectX style
// (green is the slope down the picture), with u east and v south.
//=========================================================================================================================
HEADER
{
	Description = "Cerro Blanco land: four ground materials blended by a painted splat over the landscape's grid";
}

FEATURES
{
	#include "common/features.hlsl"
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

	PixelInput MainVs( VertexInput i )
	{
		return FinalizeVertex( ProcessVertex( i ) );
	}
}

//=========================================================================================================================

PS
{
	#include "common/pixel.hlsl"

	#if ( S_MODE_DEPTH == 0 )
		RenderState( DepthFunc, EQUAL );
		RenderState( DepthWriteEnable, false );
	#endif

	// The play's rectangle in plan (west, east, south, north), how far out each spacing reaches, and the spacings
	float4 g_vPlay < Default4( -2560.0, 2520.0, -3250.0, 3080.0 ); UiGroup( "Land,10/10" ); >;
	float3 g_vZones < Default3( 3000.0, 14000.0, 46000.0 ); UiGroup( "Land,10/20" ); >;
	float3 g_vSpacing < Default3( 100.0, 350.0, 1600.0 ); UiGroup( "Land,10/30" ); >;
	float g_flSplatSize < Default( 1024.0 ); UiGroup( "Land,10/40" ); >;
	// The materials' tile in inches, close and far, and the distances over which the far one takes over
	float g_flTile < Default( 150.0 ); UiGroup( "Land,10/50" ); >;
	float g_flFarTile < Default( 1180.0 ); UiGroup( "Land,10/60" ); >;
	float2 g_vFarFade < Default2( 1800.0, 9000.0 ); UiGroup( "Land,10/70" ); >;
	// How deep the height blend reaches (larger is softer), and how strong the heights are against the splat
	float g_flBlendDepth < Default( 0.16 ); Range( 0.01, 1.0 ); UiGroup( "Land,10/80" ); >;
	float g_flHeightScale < Default( 0.55 ); Range( 0.0, 2.0 ); UiGroup( "Land,10/90" ); >;
	// The splat's broad light and dark: how strongly its alpha brightens and darkens the land
	float g_flMacro < Default( 0.5 ); Range( 0.0, 1.0 ); UiGroup( "Land,10/100" ); >;
	// Normal strength close up and far off
	float2 g_vNormalStrength < Default2( 1.0, 0.35 ); UiGroup( "Land,10/110" ); >;
	// Roughness of dry meadow, green meadow, dirt and rock
	float4 g_vRoughness < Default4( 0.93, 0.9, 0.9, 0.8 ); UiGroup( "Land,10/120" ); >;
	float3 g_vTintDry < Default3( 1.0, 1.0, 1.0 ); UiGroup( "Tint,20/10" ); >;
	float3 g_vTintGreen < Default3( 1.0, 1.0, 1.0 ); UiGroup( "Tint,20/20" ); >;
	float3 g_vTintDirt < Default3( 1.0, 1.0, 1.0 ); UiGroup( "Tint,20/30" ); >;
	float3 g_vTintRock < Default3( 1.0, 1.0, 1.0 ); UiGroup( "Tint,20/40" ); >;

	CreateInputTexture2D( Splat, Linear, 8, "", "_splat", "Land,10/130", Default4( 0.0, 0.0, 0.0, 0.5 ) );
	Texture2D g_tSplat < Channel( RGBA, Box( Splat ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( ColorDry, Srgb, 8, "", "_color", "Dry,30/10", Default3( 0.55, 0.5, 0.35 ) );
	CreateInputTexture2D( HeightDry, Linear, 8, "", "_height", "Dry,30/20", Default( 0.5 ) );
	CreateInputTexture2D( NormalDry, Linear, 8, "", "_normal", "Dry,30/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorDry < Channel( RGB, Box( ColorDry ), Srgb ); Channel( A, Box( HeightDry ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalDry < Channel( RGB, Box( NormalDry ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( ColorGreen, Srgb, 8, "", "_color", "Green,31/10", Default3( 0.35, 0.4, 0.25 ) );
	CreateInputTexture2D( HeightGreen, Linear, 8, "", "_height", "Green,31/20", Default( 0.5 ) );
	CreateInputTexture2D( NormalGreen, Linear, 8, "", "_normal", "Green,31/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorGreen < Channel( RGB, Box( ColorGreen ), Srgb ); Channel( A, Box( HeightGreen ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalGreen < Channel( RGB, Box( NormalGreen ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( ColorDirt, Srgb, 8, "", "_color", "Dirt,32/10", Default3( 0.45, 0.38, 0.3 ) );
	CreateInputTexture2D( HeightDirt, Linear, 8, "", "_height", "Dirt,32/20", Default( 0.5 ) );
	CreateInputTexture2D( NormalDirt, Linear, 8, "", "_normal", "Dirt,32/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorDirt < Channel( RGB, Box( ColorDirt ), Srgb ); Channel( A, Box( HeightDirt ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalDirt < Channel( RGB, Box( NormalDirt ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( ColorRock, Srgb, 8, "", "_color", "Rock,33/10", Default3( 0.6, 0.58, 0.54 ) );
	CreateInputTexture2D( HeightRock, Linear, 8, "", "_height", "Rock,33/20", Default( 0.5 ) );
	CreateInputTexture2D( NormalRock, Linear, 8, "", "_normal", "Rock,33/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorRock < Channel( RGB, Box( ColorRock ), Srgb ); Channel( A, Box( HeightRock ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalRock < Channel( RGB, Box( NormalRock ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	TextureAttribute( LightSim_DiffuseAlbedoTexture, g_tColorDry );
	TextureAttribute( RepresentativeTexture, g_tColorDry );

	SamplerState g_sSplat < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
	SamplerState g_sGround < Filter( ANISO ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;

	// How far along the splat a plan coordinate is (0 to 1): the grid's cells counted from the land's far edge.
	float MapAxis( float x, float lo, float hi )
	{
		float a0 = lo - g_vZones.z, a1 = lo - g_vZones.y, a2 = lo - g_vZones.x;
		float a3 = hi + g_vZones.x, a4 = hi + g_vZones.y, a5 = hi + g_vZones.z;
		float cells = ( clamp( x, a0, a1 ) - a0 ) / g_vSpacing.z + ( clamp( x, a1, a2 ) - a1 ) / g_vSpacing.y
			+ ( clamp( x, a2, a3 ) - a2 ) / g_vSpacing.x + ( clamp( x, a3, a4 ) - a3 ) / g_vSpacing.y
			+ ( clamp( x, a4, a5 ) - a4 ) / g_vSpacing.z;
		float total = ( a1 - a0 ) / g_vSpacing.z + ( a2 - a1 ) / g_vSpacing.y + ( a3 - a2 ) / g_vSpacing.x
			+ ( a4 - a3 ) / g_vSpacing.y + ( a5 - a4 ) / g_vSpacing.z;
		// Texel centres at both ends.
		return ( cells / total ) * ( g_flSplatSize - 1.0 ) / g_flSplatSize + 0.5 / g_flSplatSize;
	}

	#if ( S_MODE_DEPTH == 0 )
		[earlydepthstencil]
	#endif
	float4 MainPs( PixelInput i ) : SV_Target0
	{
		Material m = Material::Init( i );

		// Plan: east is the world's -y, north its x
		float2 vPlan = float2( -m.WorldPosition.y, m.WorldPosition.x );
		float flDistance = length( i.vPositionWithOffsetWs.xyz );

		float2 vSplatUv = float2( MapAxis( vPlan.x, g_vPlay.x, g_vPlay.y ), 1.0 - MapAxis( vPlan.y, g_vPlay.z, g_vPlay.w ) );
		float4 vSplat = g_tSplat.Sample( g_sSplat, vSplatUv );

		// The materials, u east and v south, at their real size.
		float2 vUv = float2( vPlan.x, -vPlan.y ) / g_flTile;
		float2 vDx = ddx( vUv ), vDy = ddy( vUv );
		float4 cDry = g_tColorDry.SampleGrad( g_sGround, vUv, vDx, vDy );
		float4 cGreen = g_tColorGreen.SampleGrad( g_sGround, vUv + 0.31, vDx, vDy );
		float4 cDirt = g_tColorDirt.SampleGrad( g_sGround, vUv + 0.57, vDx, vDy );
		float4 cRock = g_tColorRock.SampleGrad( g_sGround, vUv * 0.62 + 0.13, vDx * 0.62, vDy * 0.62 );

		// Height blend: each material's share of the splat, raised by its own height, and only the top of the pile shows.
		float4 vWeight = float4( saturate( 1.0 - vSplat.r - vSplat.g - vSplat.b ), vSplat.rgb );
		float4 vHeight = float4( cDry.a, cGreen.a, cDirt.a, cRock.a ) * g_flHeightScale + vWeight;
		vHeight = lerp( -1.0, vHeight, step( 0.001, vWeight ) );
		float flTop = max( max( vHeight.x, vHeight.y ), max( vHeight.z, vHeight.w ) ) - g_flBlendDepth;
		float4 vBlend = max( vHeight - flTop, 0.0 );
		vBlend /= max( dot( vBlend, 1.0 ), 0.0001 );

		float3 vAlbedo = cDry.rgb * g_vTintDry * vBlend.x + cGreen.rgb * g_vTintGreen * vBlend.y
			+ cDirt.rgb * g_vTintDirt * vBlend.z + cRock.rgb * g_vTintRock * vBlend.w;

		// Further off, the same ground at a coarser scale takes over, so the close tile's pattern doesn't repeat across the
		// hills.
		float flFar = smoothstep( g_vFarFade.x, g_vFarFade.y, flDistance );
		[branch] if ( flFar > 0.0 )
		{
			float2 vFarUv = float2( vPlan.x, -vPlan.y ) / g_flFarTile + 0.37;
			float2 vFx = ddx( vFarUv ), vFy = ddy( vFarUv );
			float3 vFarAlbedo = g_tColorDry.SampleGrad( g_sGround, vFarUv, vFx, vFy ).rgb * g_vTintDry * vBlend.x
				+ g_tColorGreen.SampleGrad( g_sGround, vFarUv + 0.21, vFx, vFy ).rgb * g_vTintGreen * vBlend.y
				+ g_tColorDirt.SampleGrad( g_sGround, vFarUv + 0.47, vFx, vFy ).rgb * g_vTintDirt * vBlend.z
				+ g_tColorRock.SampleGrad( g_sGround, vFarUv + 0.71, vFx, vFy ).rgb * g_vTintRock * vBlend.w;
			vAlbedo = lerp( vAlbedo, vFarAlbedo, flFar * 0.65 );
		}
		// The land's broad light and dark (the splat's alpha, 0.5 neutral).
		vAlbedo *= lerp( 1.0, 0.55 + 0.9 * vSplat.a, g_flMacro );

		// Normals: DirectX style, u east, v south (green is the slope towards the south).
		float3 nDry = g_tNormalDry.SampleGrad( g_sGround, vUv, vDx, vDy ).rgb * 2.0 - 1.0;
		float3 nGreen = g_tNormalGreen.SampleGrad( g_sGround, vUv + 0.31, vDx, vDy ).rgb * 2.0 - 1.0;
		float3 nDirt = g_tNormalDirt.SampleGrad( g_sGround, vUv + 0.57, vDx, vDy ).rgb * 2.0 - 1.0;
		float3 nRock = g_tNormalRock.SampleGrad( g_sGround, vUv * 0.62 + 0.13, vDx * 0.62, vDy * 0.62 ).rgb * 2.0 - 1.0;
		float3 vTangent = nDry * vBlend.x + nGreen * vBlend.y + nDirt * vBlend.z + nRock * vBlend.w;
		vTangent.xy *= lerp( g_vNormalStrength.x, g_vNormalStrength.y, smoothstep( 600.0, 6000.0, flDistance ) );
		vTangent = normalize( float3( vTangent.xy, max( vTangent.z, 0.05 ) ) );

		float3 vSurface = normalize( i.vNormalWs.xyz );
		float3 vEast = float3( 0.0, -1.0, 0.0 ), vNorth = float3( 1.0, 0.0, 0.0 );
		float3 vT = normalize( vEast - vSurface * dot( vSurface, vEast ) );
		float3 vB = normalize( vNorth - vSurface * dot( vSurface, vNorth ) );
		m.Normal = normalize( vT * vTangent.x - vB * vTangent.y + vSurface * vTangent.z );
		m.Albedo = saturate( vAlbedo );
		m.Roughness = dot( vBlend, g_vRoughness );
		m.Metalness = 0.0;
		m.AmbientOcclusion = 1.0;
		return ShadingModelStandard::Shade( i, m );
	}
}
