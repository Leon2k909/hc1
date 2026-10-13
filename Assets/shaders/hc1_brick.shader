HEADER
{
    Description = "Lowtide masonry: seamless scanned clay, recessed mortar and physical brick scale";
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
    float4 g_vBrickScale < Default4( 1, 1, 0, 0 ); UiGroup( "Brick" ); >;

    float BrickNoise( float2 p )
    {
        float2 cell = floor( p );
        float2 blend = frac( p );
        blend = blend * blend * ( 3.0 - 2.0 * blend );
        float4 dots = float4( dot( cell, float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 0 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 0, 1 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 1 ), float2( 127.1, 311.7 ) ) );
        float4 values = frac( sin( dots ) * 43758.5453 );
        return lerp( lerp( values.x, values.y, blend.x ), lerp( values.z, values.w, blend.x ), blend.y );
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        float2 worldUv = input.vTextureCoords.xy;
        // Preserve UV derivatives across repeats: the wrapping sampler handles the tile boundary and mipmaps.
        input.vTextureCoords.xy *= g_vBrickScale.xy;
        Material material = Material::From( input );
        // CommonInputs defaults metalness and transmission to one. Fired clay and mortar are opaque dielectrics.
        material.Metalness = 0.0;
        material.Transmission = 0.0;
        // Restrained variation across several metres reduces repeated tile colour without extra texture samples.
        material.Albedo *= lerp( 0.94, 1.04, BrickNoise( worldUv * 0.37 ) );
        return ShadingModelStandard::Shade( input, material );
    }
}
