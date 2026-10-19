HEADER
{
    Description = "Sewage outfalls: moving broken water sheets and aerated foam";
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
    #define S_SPECULAR 1
    #define S_TRANSLUCENT 1
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
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"
    BoolAttribute(DoNotCastShadows, true);
    RenderState(DepthWriteEnable, false);
    RenderState(BlendEnable, true);
    RenderState(SrcBlend, SRC_ALPHA);
    RenderState(DstBlend, INV_SRC_ALPHA);
    RenderState(CullMode, NONE);
    float3 g_vFlowTint < UiType(Color); Default3(.3,.45,.36); >;
    float g_flFlowSpeed < Default(1.6); >;
    float hash21(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float noise21(float2 p)
    {
        float2 ip=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(hash21(ip),hash21(ip+float2(1,0)),f.x),lerp(hash21(ip+float2(0,1)),hash21(ip+1),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        float2 uv=i.vTextureCoords.xy;
        // Cascade UVs increase from the outfall lip to the bottom of the fall.
        // Scroll toward that lower end; the former sign made the water climb.
        float2 flow=float2(uv.x*11,uv.y*4+g_flTime*g_flFlowSpeed*4);
        float a=noise21(flow), b=noise21(flow*2.63+6.7);
        float streak=noise21(float2(uv.x*52,uv.y*2+g_flTime*g_flFlowSpeed*2));
        float froth=smoothstep(.45,.86,a*.52+b*.30+streak*.18);
        float edge=smoothstep(0,.14,uv.x)*smoothstep(0,.14,1-uv.x);
        Material m=Material::Init(i);
        m.Albedo=lerp(g_vFlowTint*.3,float3(.62,.74,.65),froth);
        m.Normal=normalize(i.vNormalWs + i.vTangentUWs*(streak-.5)*.55 + i.vTangentVWs*(a-.5)*.25);
        m.Roughness=lerp(.12,.48,froth);
        m.Metalness=0;
        m.AmbientOcclusion=1;
        m.Opacity=1;
        m.Emission=g_vFlowTint*froth*.045;
        float3 lit=ShadingModelStandard::Shade(i,m).rgb;
        return float4(lit,edge*lerp(.27,.90,saturate(froth+streak*.4)));
    }
}
