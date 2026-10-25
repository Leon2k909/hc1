HEADER
{
    Description = "Forest Base scanned mineral shore with a waterline wetness band";
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
    float ShoreSoil < Default(0); Range(0,1); UiGroup("Shore"); >;
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float wet=1-smoothstep(-252,-205,m.WorldPosition.z);
        float3 dryTint=lerp(float3(.68,.73,.71),float3(.58,.65,.52),ShoreSoil);
        float3 wetTint=lerp(float3(.38,.45,.46),float3(.31,.38,.30),ShoreSoil);
        m.Albedo*=lerp(dryTint,wetTint,wet);
        m.Roughness=clamp(lerp(m.Roughness,.30,wet*.75),.30,.94);
        m.Metalness=0;
        m.Opacity=1;
        return ShadingModelStandard::Shade(i,m);
    }
}
