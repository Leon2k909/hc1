HEADER
{
    Description = "Lowtide aged cast-iron window enamel";
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
    float3 g_vEnamelTint < Default3( .065, .115, .082 ); UiType( Color ); >;
    float g_flEnamelScale < Default( 5.08 ); Range( .25, 16 ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        i.vTextureCoords.xy *= g_flEnamelScale;
        Material m = Material::From( i );
        // The same neutral scan tints both paint colours. Normalizing its
        // reflectance preserves the authored hue without washing out the wear.
        m.Albedo *= g_vEnamelTint / .285;
        m.Metalness = 0;
        m.Transmission = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
