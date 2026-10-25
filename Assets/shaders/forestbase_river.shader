HEADER
{
    Description = "Forest Base: opaque deep gorge water with small moving ripples";
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
    #include "common/pixel.hlsl"
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float3 p=m.WorldPosition;
        float a=sin(p.x*.033+g_flTime*2.3)*cos(p.y*.029-g_flTime*.83);
        float b=sin(p.x*.071-g_flTime*1.4)*sin(p.y*.053+g_flTime*1.2);
        m.Normal=normalize(m.Normal+float3(a*.085,b*.065,0));
        m.Albedo=float3(.022,.047,.054);
        m.Roughness=.12;
        m.Metalness=0;
        m.AmbientOcclusion=1;
        m.Opacity=1;
        if(DepthNormals::WantsDepthNormals())
            return DepthNormals::Output(m.Normal,m.Roughness,1);
        return ShadingModelStandard::Shade(i,m);
    }
}
