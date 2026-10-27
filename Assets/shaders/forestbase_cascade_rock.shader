HEADER
{
    Description = "Forest Base weathered wet cascade escarpment";
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
        float e=-m.WorldPosition.y,z=m.WorldPosition.z;
        float veins=sin(e*.031+sin(z*.007)*2)*sin(e*.012+z*.004);
        float wet=saturate(.35+.22*veins+.45*exp(-pow((e-430)/450,2)));
        m.Albedo*=lerp(float3(.63,.66,.68),float3(.38,.43,.45),wet);
        m.Roughness=clamp(m.Roughness*lerp(1,.60,wet),.24,.92);
        m.Metalness=0;
        return ShadingModelStandard::Shade(i,m);
    }
}
