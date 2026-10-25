HEADER
{
    Description = "Forest Base plunge water: impact ripples and broken surface froth";
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
    SamplerState WaterSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    CreateInputTexture2D(FrothMask,Linear,8,"","_mask","Water",Default3(0,0,0));
    Texture2D FrothTexture < Channel(R,Box(FrothMask),Linear); OutputFormat(BC7); SrgbRead(false); >;
    float ImpactEast0 < Default(190); UiGroup("Water"); >;
    float ImpactNorth0 < Default(3178); UiGroup("Water"); >;
    float ImpactEast1 < Default(345); UiGroup("Water"); >;
    float ImpactNorth1 < Default(3201); UiGroup("Water"); >;
    float ImpactEast2 < Default(530); UiGroup("Water"); >;
    float ImpactNorth2 < Default(3269); UiGroup("Water"); >;
    float ImpactEast3 < Default(680); UiGroup("Water"); >;
    float ImpactNorth3 < Default(3366); UiGroup("Water"); >;

    // x/y are slope in world axes; z is the local aerated-water envelope.
    float3 Impact(float2 p,float2 origin,float phase)
    {
        float2 q=p-origin;
        float d=max(length(q),1);
        float envelope=exp(-d/190)*smoothstep(8,38,d)*(1-smoothstep(390,540,d));
        float slope=.18*cos(d*.092-g_flTime*4.2+phase)*envelope;
        float2 trail=(q+float2(45,0))/float2(160,75);
        float froth=exp(-dot(trail,trail)*1.5);
        return float3(q/d*slope,froth);
    }

    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 p=m.WorldPosition.xy;
        float3 a=Impact(p,float2(ImpactNorth0,-ImpactEast0),0);
        float3 b=Impact(p,float2(ImpactNorth1,-ImpactEast1),1.7);
        float3 c=Impact(p,float2(ImpactNorth2,-ImpactEast2),3.4);
        float3 d=Impact(p,float2(ImpactNorth3,-ImpactEast3),5.1);
        float2 ripple=a.xy+b.xy+c.xy+d.xy;
        ripple+=float2(sin(p.x*.061-g_flTime*1.8)*cos(p.y*.047+g_flTime*.7),
                       cos(p.x*.037+g_flTime*.8)*sin(p.y*.079-g_flTime*1.4))*.065;
        m.Normal=normalize(m.Normal+float3(ripple,0));
        float churn=max(max(a.z,b.z),max(c.z,d.z));
        float2 flow=float2(-g_flTime*.045,sin(g_flTime*.23)*.015);
        float coarse=FrothTexture.Sample(WaterSampler,p*float2(.004,.007)+flow).r;
        float fine=FrothTexture.Sample(WaterSampler,p*float2(.017,.023)+flow*1.6+.31).r;
        // Preserve the texture's soft density. A threshold turned the sparse
        // veins into hard repeated white chips across the front of the pool.
        float foam=saturate(coarse*.65+fine*.35)*churn*.9;
        float wave=sin(p.x*.009+p.y*.011-g_flTime*.6)*.5+.5;
        m.Albedo=lerp(lerp(float3(.019,.038,.041),float3(.032,.059,.060),wave),float3(.54,.61,.63),foam);
        m.Emission=float3(.035,.045,.05)*foam;
        m.Roughness=lerp(.085+churn*.065,.51,foam);
        m.Metalness=0;
        m.AmbientOcclusion=1;
        m.Opacity=1;
        if(DepthNormals::WantsDepthNormals())
            return DepthNormals::Output(m.Normal,m.Roughness,1);
        return ShadingModelStandard::Shade(i,m);
    }
}
