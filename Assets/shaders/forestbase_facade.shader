HEADER
{
    Description = "Forest Base scanned concrete facade, cool neutral mineral surface";
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
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        // Keep the scan's pore/chip detail while removing the beige base colour.
        float mineral=dot(m.Albedo,float3(.2126,.7152,.0722));
        m.Albedo=lerp(m.Albedo,mineral.xxx,.78);
        m.Metalness=0;
        m.Roughness=clamp(m.Roughness,.58,.96);
        m.Opacity=1;
        return ShadingModelStandard::Shade(i,m);
    }
}
