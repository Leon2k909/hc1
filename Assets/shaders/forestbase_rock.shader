HEADER
{
    Description = "Forest Base cool wet boulders with slope-dependent moss";
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
    float RockDesaturation < Default(0.82); Range(0,1); UiGroup("Rock"); >;
    float RockWetness < Default(0.55); Range(0,1); UiGroup("Rock"); >;
    float MossAmount < Default(0.80); Range(0,1); UiGroup("Rock"); >;
    float3 RockTint < Default3(0.78,0.84,0.86); UiType(Color); UiGroup("Rock"); >;
    float3 MossTint < Default3(0.035,0.065,0.025); UiType(Color); UiGroup("Rock"); >;

    float RockHash(float2 p)
    {
        float3 q=frac(p.xyx*.1031);
        q+=dot(q,q.yzx+33.33);
        return frac((q.x+q.y)*q.z);
    }
    float RockNoise(float2 p)
    {
        float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(RockHash(a),RockHash(a+float2(1,0)),f.x),
                    lerp(RockHash(a+float2(0,1)),RockHash(a+1),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float3 p=m.WorldPosition;
        float coarse=RockNoise(p.xy*.0075+p.z*.002);
        float streak=RockNoise(float2(p.x*.024+p.y*.011,p.z*.002));
        float up=saturate(normalize(i.vNormalWs).z);
        float cover=.65*coarse+.35*streak+.15*(1-m.Roughness);
        float moss=MossAmount*smoothstep(.22,.78,up)*smoothstep(.30,.68,cover);
        float wet=saturate(RockWetness+.24*(streak-.5)+.30*(1-smoothstep(-285,-155,p.z)));
        float luminance=dot(m.Albedo,float3(.2126,.7152,.0722));
        float3 stone=lerp(m.Albedo,luminance.xxx,RockDesaturation)*RockTint*lerp(1,.62,wet);
        float3 mossColor=MossTint*(.55+1.5*luminance);
        m.Albedo=lerp(stone,mossColor,moss);
        float rough=lerp(max(.48,m.Roughness),.25,wet*.7);
        m.Roughness=lerp(rough,lerp(.90,.75,wet),moss);
        m.Normal=normalize(lerp(m.Normal,normalize(i.vNormalWs),wet*.12*(1-moss)));
        m.Metalness=0;
        m.Opacity=1;
        return ShadingModelStandard::Shade(i,m);
    }
}
