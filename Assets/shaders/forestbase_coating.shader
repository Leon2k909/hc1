HEADER
{
    Description = "Forest Base PBR powder coating with explicit dielectric metalness";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth(S_MODE_DEPTH);
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
    PixelInput MainVs(VertexInput i) { return FinalizeVertex(ProcessVertex(i)); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float g_flCoatingMetalness < Default(0.0); Range(0,1); UiGroup("Coating"); >;
    float CoatingDesaturation < Default(0.0); Range(0,1); UiGroup("Coating"); >;
    float3 CoatingTint < Default3(1,1,1); UiType(Color); UiGroup("Coating"); >;
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float neutral=dot(m.Albedo,float3(.2126,.7152,.0722));
        m.Albedo=lerp(m.Albedo,neutral.xxx,CoatingDesaturation)*CoatingTint;
        m.Metalness=g_flCoatingMetalness;
        m.Roughness=clamp(m.Roughness,.20,.95);
        m.Opacity=1;
        return ShadingModelStandard::Shade(i,m);
    }
}
