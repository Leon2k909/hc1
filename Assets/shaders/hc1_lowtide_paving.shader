HEADER
{
    Description = "Lowtide granite paving: original scan pixels, shallow relief and consistent filtering";
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
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float4 g_vPavingRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Paving" ); >;
    float2 g_vPavingScale < Default2( 1, 1 ); UiGroup( "Paving" ); >;

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        float2 repeat = input.vTextureCoords.xy * g_vPavingScale;
        float2 uv = g_vPavingRegion.xy + frac( repeat ) * g_vPavingRegion.zw;
        // Derivatives must be taken before frac: otherwise every atlas wrap
        // chooses a distant mip and paints a blurry line across the pavement.
        float2 dx = ddx( repeat ) * g_vPavingRegion.zw;
        float2 dy = ddy( repeat ) * g_vPavingRegion.zw;
        float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );
        Material material = Material::Init( input );
        material.Albedo = color.rgb * g_flTintColor * input.vVertexColor.rgb;
        material.Normal = TransformNormal( DecodeNormal( normal.xyz ), input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
        material.Roughness = rma.r;
        material.Metalness = 0.0;
        material.AmbientOcclusion = rma.b;
        material.Opacity = 1.0;
        return ShadingModelStandard::Shade( input, material );
    }
}
