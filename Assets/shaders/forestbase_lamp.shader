HEADER
{
    Description = "Forest Base warm diffused fixture glass";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
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
    PixelInput MainVs(VertexInput i) { return FinalizeVertex(ProcessVertex(i)); }
}
PS
{
    #include "common/pixel.hlsl"
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        // A uniform opal diffuser stays stable when a distant fixture is only
        // a few pixels tall. Repeated UV borders had no minification filter.
        m.Albedo=float3(.3,.25,.2);
        m.Emission=float3(3.5,2.5,1.5);
        m.Metalness=0;
        m.Roughness=.8;
        m.Opacity=1;
        return ShadingModelStandard::Shade(i,m);
    }
}
