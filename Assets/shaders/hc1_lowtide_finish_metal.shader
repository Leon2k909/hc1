HEADER
{
    Description = "Lowtide finish metal: sample the original scan instead of its padded border";
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
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float4 g_vFinishRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Finish" ); >;
    float g_flFinishScale < Default( 1.5 ); Range( .1, 8 ); UiGroup( "Finish" ); >;
    float g_flFinishRoughness < Default( .62 ); Range( 0, 1 ); UiGroup( "Finish" ); >;
    float g_flFinishMetalness < Default( .45 ); Range( 0, 1 ); UiGroup( "Finish" ); >;

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        float2 repeat = input.vTextureCoords.xy * g_flFinishScale;
        float2 uv = g_vFinishRegion.xy + frac( repeat ) * g_vFinishRegion.zw;
        // Calculate gradients before wrapping to avoid a false distant mip at
        // each repeat seam. The source colour/normal pixels stay unchanged.
        float2 dx = ddx( repeat ) * g_vFinishRegion.zw;
        float2 dy = ddy( repeat ) * g_vFinishRegion.zw;
        float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        Material material = Material::Init( input );
        material.Albedo = color.rgb * g_flTintColor * input.vVertexColor.rgb;
        material.Normal = TransformNormal( DecodeNormal( normal.rgb ), input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
        material.Roughness = g_flFinishRoughness;
        material.Metalness = g_flFinishMetalness;
        material.AmbientOcclusion = 1.0;
        material.Opacity = color.a;
        return ShadingModelStandard::Shade( input, material );
    }
}
