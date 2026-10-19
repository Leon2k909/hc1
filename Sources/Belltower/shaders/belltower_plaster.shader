HEADER
{
    Description = "Belltower limewash with photographed peeling render and sheltered wear";
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
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    CreateInputTexture2D( TextureWearColor, Srgb, 8, "", "_color", "Weathering,20/10", Default3( .6, .5, .4 ) );
    CreateInputTexture2D( TextureWearNormal, Linear, 8, "NormalizeNormals", "_normal", "Weathering,20/20", Default3( .5, .5, 1 ) );
    CreateInputTexture2D( TextureWearRoughness, Linear, 8, "", "_rough", "Weathering,20/30", Default( .8 ) );
    CreateInputTexture2D( TextureWearAo, Linear, 8, "", "_ao", "Weathering,20/40", Default( 1 ) );
    CreateInputTexture2D( TextureWearHeight, Linear, 8, "", "_height", "Weathering,20/50", Default( .5 ) );
    Texture2D g_tWearColor < Channel( RGB, Box( TextureWearColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tWearNormal < Channel( RGB, Box( TextureWearNormal ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    Texture2D g_tWearData < Channel( R, Box( TextureWearRoughness ), Linear ); Channel( G, Box( TextureWearHeight ), Linear ); Channel( B, Box( TextureWearAo ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    float2 g_vPlasterUvScale < Default2( 6.5024, 6.5024 ); UiGroup( "Weathering,20/60" ); >;
    float2 g_vWearUvScale < Default2( 8.66987, 8.66987 ); UiGroup( "Weathering,20/70" ); >;
    float g_flWearCoverage < Default( .42 ); Range( 0, 1 ); UiGroup( "Weathering,20/80" ); >;
    float g_flWearBrightness < Default( 2.6 ); Range( .5, 5 ); UiGroup( "Weathering,20/90" ); >;

    // Broad, continuous patches hide the scan's tile repetition. World position
    // keeps separate wall polygons continuous and makes each street frontage differ.
    float HashPlaster( float2 p )
    {
        return frac( sin( dot( p, float2( 127.1, 311.7 ) ) ) * 43758.5453 );
    }
    float NoisePlaster( float2 p )
    {
        float2 cell = floor( p ), f = frac( p );
        f = f * f * ( 3.0 - 2.0 * f );
        return lerp( lerp( HashPlaster( cell ), HashPlaster( cell + float2( 1, 0 ) ), f.x ),
                     lerp( HashPlaster( cell + float2( 0, 1 ) ), HashPlaster( cell + 1 ), f.x ), f.y );
    }

    // Two continuously warped scan samples interrupt repeated peeling shapes.
    // Continuous coordinates avoid cell boundaries on large uninterrupted walls.
    void SampleWornPlaster( float2 uv, out float3 color, out float3 normal, out float3 data )
    {
        float2 warp = .35 * float2( NoisePlaster( uv * .21 ), NoisePlaster( uv * .21 + 11.9 ) );
        float2 ua = uv + warp;
        float2 ub = uv * 1.13 + float2( 3.17, 7.83 ) - warp;
        float blend = smoothstep( .30, .70, NoisePlaster( uv * .43 + 9.3 ) );
        float2 dxa = ddx( ua ), dya = ddy( ua ), dxb = ddx( ub ), dyb = ddy( ub );
        float3 da = g_tWearData.SampleGrad( TextureFiltering, ua, dxa, dya ).rgb;
        float3 db = g_tWearData.SampleGrad( TextureFiltering, ub, dxb, dyb ).rgb;
        color = lerp( g_tWearColor.SampleGrad( TextureFiltering, ua, dxa, dya ).rgb,
                      g_tWearColor.SampleGrad( TextureFiltering, ub, dxb, dyb ).rgb, blend );
        normal = normalize( lerp( DecodeNormal( g_tWearNormal.SampleGrad( TextureFiltering, ua, dxa, dya ).xyz ),
                                  DecodeNormal( g_tWearNormal.SampleGrad( TextureFiltering, ub, dxb, dyb ).xyz ), blend ) );
        data = lerp( da, db, blend );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        #if !S_MODE_DEPTH
        float2 uv = i.vTextureCoords.xy * g_vPlasterUvScale;
        float2 wearUv = i.vTextureCoords.xy * g_vWearUvScale;
        float4 color = g_tColor.Sample( TextureFiltering, uv );
        float4 normal = g_tNormal.Sample( TextureFiltering, uv );
        float4 rma = g_tRma.Sample( TextureFiltering, uv );
        float3 worn, wornNormal, wornData;
        SampleWornPlaster( wearUv, worn, wornNormal, wornData );

        float3 position = m.WorldPosition;
        float side = abs( i.vNormalWs.x ) > abs( i.vNormalWs.y ) ? position.y : position.x;
        float2 wall = float2( side, position.z );
        float patch = .72 * NoisePlaster( wall / float2( 245, 175 ) )
                    + .28 * NoisePlaster( wall / float2( 61, 87 ) + 13.7 );
        float foot = 1.0 - smoothstep( 16.0, 104.0, max( 0.0, position.z ) );
        float wear = smoothstep( .60, .82, patch + .28 * foot + .42 * g_flWearCoverage );
        wear *= saturate( g_flWearCoverage * 3.0 );

        // Keep the painted layers in the town palette; recessed spalls reveal a
        // neutral lime/sand substrate. Source maps are sampled without pixel edits.
        float exposed = 1.0 - smoothstep( .29, .43, wornData.g );
        float luminance = dot( worn, float3( .2126, .7152, .0722 ) );
        float3 paintedWear = luminance * g_flWearBrightness * g_flTintColor;
        float3 substrate = luminance * 1.65 * float3( 1.06, 1.0, .86 );
        float3 wearAlbedo = lerp( paintedWear, substrate, exposed );
        m.Albedo = lerp( color.rgb * g_flTintColor, wearAlbedo, wear ) * i.vVertexColor.rgb;
        float3 tangentNormal = normalize( lerp( DecodeNormal( normal.xyz ), wornNormal, wear ) );
        m.Normal = TransformNormal( tangentNormal, i.vNormalWs, i.vTangentUWs, i.vTangentVWs );
        m.Roughness = lerp( max( .65, pow( max( rma.r, .05 ), .8 ) ), max( .72, wornData.r ), wear );
        m.AmbientOcclusion = lerp( rma.b, wornData.b, wear );
        m.TextureCoords = uv;
        m.TintMask = normal.a;
        #endif
        m.Metalness = 0;
        m.Transmission = 0;
        m.Opacity = 1;
        return ShadingModelStandard::Shade( i, m );
    }
}
