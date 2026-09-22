HEADER
{
    Description = "M4 matte anodized optic housing";
    Version = 1;
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth();
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex(i) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    RenderState( CullMode, BACK );
    float g_flUseFactoryFinish < Default(1.0); Range(0.0,1.0); UiGroup("Finish,10/10"); >;
    float4 g_vColorTint < UiType(Color); Default4(1.0,1.0,1.0,0.0); UiGroup("Finish,10/20"); >;
    float g_flRoughnessScaleFactor < Default(1.0); Range(0.0,3.0); UiGroup("Finish,10/30"); >;
    float g_flMetalness < Default(0.65); Range(0.0,1.0); UiGroup("Finish,10/40"); >;
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From(i);
        // Preserve the donor's engravings and wear, with the M4's neutral black finish.
        float luminance = dot(m.Albedo, float3(0.2126,0.7152,0.0722));
        float3 factory = (0.022 + luminance * 0.16) * float3(0.93,0.96,1.0);
        m.Albedo = lerp(m.Albedo,factory,g_flUseFactoryFinish) * g_vColorTint.rgb;
        m.Roughness = lerp(saturate(m.Roughness*g_flRoughnessScaleFactor),0.54+saturate(m.Roughness)*0.26,g_flUseFactoryFinish);
        m.Metalness = g_flMetalness;
        return ShadingModelStandard::Shade(i,m);
    }
}
