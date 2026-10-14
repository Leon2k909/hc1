HEADER
{
    Description = "Lowtide estuary silt with continuous bank moisture";
}
FEATURES {
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth( S_MODE_DEPTH );
    ToolsShadingComplexity( "tools_shading_complexity.shader" );
}
COMMON {
    #include "common/shared.hlsl"
}
struct VertexInput {
    #include "common/vertexinput.hlsl"
};
struct PixelInput {
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
    CreateInputTexture2D( TextureWetColor, Srgb, 8, "", "_color", "Wet silt", Default3( .15, .15, .15 ) );
    CreateInputTexture2D( TextureWetNormal, Linear, 8, "NormalizeNormals", "_normal", "Wet silt", Default3( .5, .5, 1 ) );
    Texture2D g_tWetColor < Channel( RGB, Box( TextureWetColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tWetNormal < Channel( RGB, Box( TextureWetNormal ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    float SiltNoise( float2 p )
    {
        float2 a = floor( p ), f = frac( p );
        f = f * f * ( 3 - 2 * f );
        float4 h = float4( dot( a, float2( 127.1, 311.7 ) ),
            dot( a + float2( 1, 0 ), float2( 127.1, 311.7 ) ),
            dot( a + float2( 0, 1 ), float2( 127.1, 311.7 ) ),
            dot( a + 1, float2( 127.1, 311.7 ) ) );
        h = frac( sin( h ) * 43758.5453 );
        return lerp( lerp( h.x, h.y, f.x ), lerp( h.z, h.w, f.x ), f.y );
    }
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        // Shared UVs and a continuous moisture field eliminate the old random
        // wet/dry material rectangles on individual terrain grid cells.
        Material m = Material::From( i );
        float2 p = m.WorldPosition.xy;
        float shore = 1 - smoothstep( 114, 205, abs( p.y ) + ( SiltNoise( p / 42 ) - .5 ) * 36 );
        float variation = SiltNoise( p / 187 ) * .65 + SiltNoise( p / 35 + 18 ) * .35;
        // Exposed tidal sediment stays damp between tides. Small hollows retain
        // a water film; raised patches break up highlights instead of becoming
        // a uniformly glossy sheet or a pale dry beach.
        float hollows = smoothstep( .28, .72, SiltNoise( p / 13 + 4.7 ) );
        float low = 1 - smoothstep( -136, -128, m.WorldPosition.z + (variation-.5)*1.8 );
        float moisture = saturate( .20 + low * .65 + shore * .18 + hollows * .14 );
        float wetBlend = smoothstep( .40, .88, moisture );
        // Original soil UVs cover 128 inches; the new cohesive silt scan covers
        // one metre. Wet fines fill the coarse dry texture's gaps at the bank.
        float2 wetUv = i.vTextureCoords.xy * 3.2512;
        float3 wetColor = g_tWetColor.Sample( TextureFiltering, wetUv ).rgb;
        float3 wetNormal = TransformNormal( DecodeNormal( g_tWetNormal.Sample( TextureFiltering, wetUv ).rgb ),
                                           i.vNormalWs, i.vTangentUWs, i.vTangentVWs );
        m.Albedo = lerp( m.Albedo, wetColor * float3( .82, .85, .85 ), wetBlend );
        m.Normal = normalize( lerp( m.Normal, wetNormal, wetBlend ) );
        m.Albedo *= float3( .74, .77, .73 ) * lerp( .65, .95, variation ) * lerp( 1, .50, moisture );
        m.Roughness = lerp( .76, .22, moisture * ( .7 + hollows * .3 ) );
        m.Metalness = 0;
        m.Transmission = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
