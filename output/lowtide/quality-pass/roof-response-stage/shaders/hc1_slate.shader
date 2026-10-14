HEADER
{
    Description = "Natural roof slate with split-stone relief and broad runoff weathering";
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
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"

    float2 g_vSlateScale < Default2( 1.2192, 1.2192 ); >;
    float g_flSlateWeathering < Default( .7 ); Range( 0, 1 ); >;

    float SlateNoise( float2 p )
    {
        float2 cell = floor( p );
        float2 blend = frac( p );
        blend = blend * blend * ( 3 - 2 * blend );
        float4 dots = float4( dot( cell, float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 0 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 0, 1 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 1 ), float2( 127.1, 311.7 ) ) );
        float4 values = frac( sin( dots ) * 43758.5453 );
        return lerp( lerp( values.x, values.y, blend.x ), lerp( values.z, values.w, blend.x ), blend.y );
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        input.vTextureCoords.xy *= g_vSlateScale;
        Material material = Material::From( input );
        material.Metalness = 0;
        material.Transmission = 0;

        // Orient broad rain deposits down the actual roof pitch. Metre-scale
        // variation survives distance filtering without adding fine geometry.
        float2 slope = normalize( input.vNormalWs.xy + float2( .00001, .00001 ) );
        float2 ridge = float2( -slope.y, slope.x );
        float3 world = material.WorldPosition;
        float2 surface = float2( dot( world.xy, ridge ), dot( world.xy, slope ) );
        float patch = SlateNoise( surface / float2( 155, 210 ) );
        float runoff = SlateNoise( surface / float2( 29, 180 ) + 37.1 );
        float weather = smoothstep( .24, .78, patch * .68 + runoff * .32 );
        material.Albedo *= lerp( 1, lerp( .54, 1.20, weather ), g_flSlateWeathering );
        material.Roughness = saturate( material.Roughness + ( .5 - weather ) * .16 * g_flSlateWeathering );
        return ShadingModelStandard::Shade( input, material );
    }
}
