//=========================================================================================================================
// HC1 vista: Belltower's land out to the horizon, painted from above (Tools/belltower_vista_paint.py).
//
// The land is painted in four zones round the town, each a texture over the town's rectangle grown by the zone's
// margin, the nearest the finest. A pixel takes the finest zone that reaches it (by how far it is out from the town east
// or west, or north or south, whichever is more), blending into the next over the last part of that zone's margin, so the
// land's texels stay about a pixel wide wherever they're seen from the town. Positions are the world's (the vista sits at
// the origin, unturned), so the mesh needs no UVs.
//
// A zone's colour carries the ground's kind in its alpha, for the roughness and the close-up detail: 0 grass, 1/3 soil
// and gravel, 2/3 stone, 1 water. Its normal map is the land's normal in plan: red east, green north. Rows run south.
//
// Near the camera the ground gets tiling detail of its kind, at two scales so it doesn't repeat, fading out with distance
// where the zones' own texels are fine enough. A detail texture's red and green tilt the normal east and north, and its
// blue brightens or darkens the colour about 0.5.
//=========================================================================================================================
HEADER
{
	Description = "HC1 vista: land painted from above in zones round the town, with tiling detail up close";
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

	// The town's rectangle in plan: west, east, south, north
	float4 g_vTown < Default4( -2380.0, 2380.0, -1466.0, 1800.0 ); UiGroup( "Vista,10/10" ); >;
	// How far out from the rectangle each zone's texture reaches
	float4 g_vZoneMargins < Default4( 1600.0, 6000.0, 34000.0, 92000.0 ); UiGroup( "Vista,10/20" ); >;
	// The share of a zone's margin over which it blends into the next
	float g_flZoneBlend < Default( 0.12 ); Range( 0.01, 0.5 ); UiGroup( "Vista,10/30" ); >;
	// Roughness of grass, soil, stone and water
	float4 g_vRoughness < Default4( 0.95, 0.9, 0.8, 0.12 ); UiGroup( "Vista,10/40" ); >;

	// The detail's tile sizes, fine and coarse, and the camera distances over which it fades out
	float2 g_vDetailTiles < Default2( 70.0, 290.0 ); UiGroup( "Detail,30/10" ); >;
	float2 g_vDetailFade < Default2( 700.0, 2600.0 ); UiGroup( "Detail,30/20" ); >;
	float g_flDetailNormal < Default( 0.8 ); Range( 0.0, 3.0 ); UiGroup( "Detail,30/30" ); >;
	float g_flDetailAlbedo < Default( 0.7 ); Range( 0.0, 1.0 ); UiGroup( "Detail,30/40" ); >;

	CreateInputTexture2D( ColorA, Srgb, 8, "", "_color", "Zone A,20/10", Default3( 0.35, 0.4, 0.25 ) );
	CreateInputTexture2D( KindA, Linear, 8, "", "_kind", "Zone A,20/20", Default( 0.0 ) );
	CreateInputTexture2D( NormalA, Linear, 8, "", "_normal", "Zone A,20/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorA < Channel( RGB, Box( ColorA ), Srgb ); Channel( A, Box( KindA ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalA < Channel( RGB, Box( NormalA ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( ColorB, Srgb, 8, "", "_color", "Zone B,21/10", Default3( 0.35, 0.4, 0.25 ) );
	CreateInputTexture2D( KindB, Linear, 8, "", "_kind", "Zone B,21/20", Default( 0.0 ) );
	CreateInputTexture2D( NormalB, Linear, 8, "", "_normal", "Zone B,21/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorB < Channel( RGB, Box( ColorB ), Srgb ); Channel( A, Box( KindB ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalB < Channel( RGB, Box( NormalB ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( ColorC, Srgb, 8, "", "_color", "Zone C,22/10", Default3( 0.35, 0.4, 0.25 ) );
	CreateInputTexture2D( KindC, Linear, 8, "", "_kind", "Zone C,22/20", Default( 0.0 ) );
	CreateInputTexture2D( NormalC, Linear, 8, "", "_normal", "Zone C,22/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorC < Channel( RGB, Box( ColorC ), Srgb ); Channel( A, Box( KindC ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalC < Channel( RGB, Box( NormalC ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( ColorD, Srgb, 8, "", "_color", "Zone D,23/10", Default3( 0.35, 0.4, 0.25 ) );
	CreateInputTexture2D( KindD, Linear, 8, "", "_kind", "Zone D,23/20", Default( 0.0 ) );
	CreateInputTexture2D( NormalD, Linear, 8, "", "_normal", "Zone D,23/30", Default3( 0.5, 0.5, 1.0 ) );
	Texture2D g_tColorD < Channel( RGB, Box( ColorD ), Srgb ); Channel( A, Box( KindD ), Linear ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tNormalD < Channel( RGB, Box( NormalD ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	CreateInputTexture2D( DetailGrass, Linear, 8, "", "_detail", "Detail,30/50", Default3( 0.5, 0.5, 0.5 ) );
	CreateInputTexture2D( DetailSoil, Linear, 8, "", "_detail", "Detail,30/60", Default3( 0.5, 0.5, 0.5 ) );
	CreateInputTexture2D( DetailStone, Linear, 8, "", "_detail", "Detail,30/70", Default3( 0.5, 0.5, 0.5 ) );
	Texture2D g_tDetailGrass < Channel( RGB, Box( DetailGrass ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
	Texture2D g_tDetailSoil < Channel( RGB, Box( DetailSoil ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
	Texture2D g_tDetailStone < Channel( RGB, Box( DetailStone ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

	TextureAttribute( LightSim_DiffuseAlbedoTexture, g_tColorC );
	TextureAttribute( RepresentativeTexture, g_tColorC );

	SamplerState g_sZone < Filter( ANISO ); AddressU( CLAMP ); AddressV( CLAMP ); >;
	SamplerState g_sDetail < Filter( ANISO ); AddressU( WRAP ); AddressV( WRAP ); >;

	// One zone's colour (alpha: the kind) and packed normal, weighted, at a plan point. Its texture spans the town's
	// rectangle grown by margin: u runs east from its west edge, v south from its north edge.
	void AddZone( Texture2D tColor, Texture2D tNormal, float flMargin, float flWeight, float2 vPlan, float2 vDx, float2 vDy,
		inout float4 vColor, inout float3 vPacked )
	{
		float2 vCorner = float2( g_vTown.x - flMargin, g_vTown.w + flMargin );
		float2 vSize = float2( g_vTown.y - g_vTown.x, g_vTown.w - g_vTown.z ) + 2.0 * flMargin;
		float2 vScale = float2( 1.0, -1.0 ) / vSize;
		float2 vUv = ( vPlan - vCorner ) * vScale;
		vColor += flWeight * tColor.SampleGrad( g_sZone, vUv, vDx * vScale, vDy * vScale );
		vPacked += flWeight * tNormal.SampleGrad( g_sZone, vUv, vDx * vScale, vDy * vScale ).rgb;
	}

	// A detail texture at both scales: ( east tilt, north tilt, brightness ).
	float3 Detail( Texture2D tDetail, float2 vPlan, float2 vDx, float2 vDy )
	{
		float2 vFlip = float2( 1.0, -1.0 );
		float2 vFine = vFlip / g_vDetailTiles.x;
		float2 vCoarse = vFlip / g_vDetailTiles.y;
		float3 a = tDetail.SampleGrad( g_sDetail, vPlan * vFine, vDx * vFine, vDy * vFine ).rgb;
		float3 b = tDetail.SampleGrad( g_sDetail, vPlan * vCoarse + 0.37, vDx * vCoarse, vDy * vCoarse ).rgb;
		float2 vTilt = ( a.rg * 2.0 - 1.0 ) + 0.6 * ( b.rg * 2.0 - 1.0 );
		return float3( vTilt, 4.0 * a.b * b.b );
	}

	#if ( S_MODE_DEPTH == 0 )
		[earlydepthstencil]
	#endif
	float4 MainPs( PixelInput i ) : SV_Target0
	{
		Material m = Material::Init( i );

		// Plan: east is the world's -y, north its x
		float2 vPlan = float2( -m.WorldPosition.y, m.WorldPosition.x );
		float2 vDx = ddx( vPlan );
		float2 vDy = ddy( vPlan );

		float flOutE = max( max( g_vTown.x - vPlan.x, vPlan.x - g_vTown.y ), 0.0 );
		float flOutN = max( max( g_vTown.z - vPlan.y, vPlan.y - g_vTown.w ), 0.0 );
		float flOut = max( flOutE, flOutN );

		float flA = 1.0 - smoothstep( g_vZoneMargins.x * ( 1.0 - g_flZoneBlend ), g_vZoneMargins.x, flOut );
		float flB = 1.0 - smoothstep( g_vZoneMargins.y * ( 1.0 - g_flZoneBlend ), g_vZoneMargins.y, flOut );
		float flC = 1.0 - smoothstep( g_vZoneMargins.z * ( 1.0 - g_flZoneBlend ), g_vZoneMargins.z, flOut );
		float4 vShare;
		vShare.x = flA;
		vShare.y = ( 1.0 - flA ) * flB;
		vShare.z = ( 1.0 - flA ) * ( 1.0 - flB ) * flC;
		vShare.w = ( 1.0 - flA ) * ( 1.0 - flB ) * ( 1.0 - flC );

		float4 vColor = 0.0;
		float3 vPacked = 0.0;
		[branch] if ( vShare.x > 0.0 )
			AddZone( g_tColorA, g_tNormalA, g_vZoneMargins.x, vShare.x, vPlan, vDx, vDy, vColor, vPacked );
		[branch] if ( vShare.y > 0.0 )
			AddZone( g_tColorB, g_tNormalB, g_vZoneMargins.y, vShare.y, vPlan, vDx, vDy, vColor, vPacked );
		[branch] if ( vShare.z > 0.0 )
			AddZone( g_tColorC, g_tNormalC, g_vZoneMargins.z, vShare.z, vPlan, vDx, vDy, vColor, vPacked );
		[branch] if ( vShare.w > 0.0 )
			AddZone( g_tColorD, g_tNormalD, g_vZoneMargins.w, vShare.w, vPlan, vDx, vDy, vColor, vPacked );

		// The land's normal in plan ( east, north, up )
		float2 vTilt = vPacked.rg * 2.0 - 1.0;
		float3 vNormal = float3( vTilt, sqrt( saturate( 1.0 - dot( vTilt, vTilt ) ) ) );

		// Grass, soil, stone, water
		float4 vKind = saturate( 1.0 - abs( vColor.a * 3.0 - float4( 0.0, 1.0, 2.0, 3.0 ) ) );
		vKind /= max( dot( vKind, 1.0 ), 0.0001 );

		float3 vAlbedo = vColor.rgb;
		float flNear = 1.0 - smoothstep( g_vDetailFade.x, g_vDetailFade.y, length( i.vPositionWithOffsetWs.xyz ) );
		[branch] if ( flNear > 0.0 )
		{
			float3 vDetail = float3( 0.0, 0.0, 1.0 ) * vKind.w;
			[branch] if ( vKind.x > 0.0 ) vDetail += vKind.x * Detail( g_tDetailGrass, vPlan, vDx, vDy );
			[branch] if ( vKind.y > 0.0 ) vDetail += vKind.y * Detail( g_tDetailSoil, vPlan, vDx, vDy );
			[branch] if ( vKind.z > 0.0 ) vDetail += vKind.z * Detail( g_tDetailStone, vPlan, vDx, vDy );
			vNormal = normalize( float3( vNormal.xy + vDetail.xy * g_flDetailNormal * flNear, vNormal.z ) );
			vAlbedo *= lerp( 1.0, vDetail.z, g_flDetailAlbedo * flNear );
		}

		m.Albedo = saturate( vAlbedo );
		m.Normal = normalize( float3( vNormal.y, -vNormal.x, vNormal.z ) );
		m.Roughness = dot( vKind, g_vRoughness );
		m.Metalness = 0.0;
		m.AmbientOcclusion = 1.0;
		return ShadingModelStandard::Shade( i, m );
	}
}
