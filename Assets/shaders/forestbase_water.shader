HEADER
{
    Description = "Forest Base: descending waterfall ribbons and gorge water";
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
    #define S_TRANSLUCENT 1
    #define BLEND_MODE_ALREADY_SET 1
    RenderState(BlendEnable, true);
    RenderState(SrcBlend, SRC_ALPHA);
    RenderState(DstBlend, INV_SRC_ALPHA);
    RenderState(DepthWriteEnable, false);
    #include "common/pixel.hlsl"
    float WaterHash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float WaterNoise(float2 p)
    {
        float2 a=floor(p); float2 f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(WaterHash(a),WaterHash(a+float2(1,0)),f.x),
                    lerp(WaterHash(a+float2(0,1)),WaterHash(a+float2(1,1)),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m = Material::From(i);
        float3 p = m.WorldPosition;
        float vertical = 1-abs(i.vNormalWs.z);
        float phase = p.z*.007+g_flTime*2.1;
        float stream = sin(phase+p.x*.033)*sin(phase*1.37+p.y*.043);
        float2 flow=float2(p.y*.032,(p.z+g_flTime*150)*.018);
        float foam = saturate(.13+WaterNoise(flow)*.64+WaterNoise(flow*4)*.28)*vertical;
        float ripple = sin(p.x*.047+g_flTime*1.7)*sin(p.y*.053-g_flTime*2.1);
        m.Albedo = lerp(float3(.025,.05,.06),float3(.66,.75,.77),foam);
        m.Normal = normalize(m.Normal+float3(ripple*.075,stream*.06,0));
        m.Roughness = .1+foam*.25;
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        float puddle = p.z > -10 && p.z < 10 ? 1 : 0;
        float edge = saturate((.48-length(i.vTextureCoords.xy-.5))*12);
        float curtainEdge=smoothstep(0,.08,i.vTextureCoords.x)*smoothstep(0,.08,1-i.vTextureCoords.x);
        float streak=WaterNoise(float2(p.y*.065,(p.z+g_flTime*190)*.005));
        m.Opacity = lerp((.32+foam*.60)*lerp(1,curtainEdge*(.55+.45*streak),vertical),edge*.42,puddle);
        return ShadingModelStandard::Shade(i,m);
    }
}
