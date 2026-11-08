HEADER
{
 Description = "AKS-74U classic Bakelite magazine";
 Version = 1;
}
FEATURES {
    #include "common/features.hlsl"
}
MODES
{
 Forward();
 Depth();
}
COMMON {
    #include "common/shared.hlsl"
}
struct VertexInput {
    #include "common/vertexinput.hlsl"
};
struct PixelInput {
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
    float g_flUseFactoryFinish < Default(1); Range(0,1); >;
    float4 g_vColorTint < UiType(Color); Default4(1,1,1,1); >;
    float g_flRoughnessScaleFactor < Default(1); Range(0,3); >;
    float hash21(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float resinNoise(float2 p)
    {
        float2 a=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(hash21(a),hash21(a+float2(1,0)),f.x),lerp(hash21(a+float2(0,1)),hash21(a+1),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 uv=i.vTextureCoords.xy;
        // The atlas's upper strips and right edge are steel. The source metalness
        // also protects the feed hardware, rivets and worn steel on body islands.
        float body=(1-smoothstep(0.3,0.65,m.Metalness))*step(0.16,uv.y)*(1-step(0.90,uv.x));
        float n=resinNoise(uv*float2(24,17));
        float swirls=resinNoise(uv*float2(95,64)+n*3);
        float fibers=resinNoise(uv*float2(450,125)+swirls*4);
        float lum=dot(m.Albedo,float3(0.2126,0.7152,0.0722));
        float detail=clamp(0.65+sqrt(max(lum,0))*2.5,0.55,1.25);
        float3 resin=lerp(float3(0.095,0.010,0.003),float3(0.25,0.043,0.009),n*0.70+swirls*0.30);
        resin*=detail*(0.94+fibers*0.12);
        float wear=smoothstep(0.06,0.22,lum)*0.28;
        resin=lerp(resin,float3(0.43,0.21,0.09),wear);
        float factory=body*g_flUseFactoryFinish;
        m.Albedo=lerp(m.Albedo,resin,factory)*g_vColorTint.rgb;
        m.Roughness=lerp(m.Roughness,0.38+swirls*0.13,factory)*g_flRoughnessScaleFactor;
        m.Metalness=lerp(m.Metalness,0,factory);
        return ShadingModelStandard::Shade(i,m);
    }
}