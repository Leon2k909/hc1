HEADER
{
    Description = "Spillway eroded alpine rock, scree, treeline and settled snow";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth(S_MODE_DEPTH);
    ToolsShadingComplexity("tools_shading_complexity.shader");
}
COMMON
{
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
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter(ANISOTROPIC); MaxAniso(8); AddressU(WRAP); AddressV(WRAP); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float N(float2 p)
    {
        float2 a=floor(p),f=frac(p); f=f*f*(3-2*f);
        float4 h=frac(sin(float4(dot(a,float2(127.1,311.7)),dot(a+float2(1,0),float2(127.1,311.7)),dot(a+float2(0,1),float2(127.1,311.7)),dot(a+1,float2(127.1,311.7))))*43758.5453);
        return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
    }
    float3 Rock(float3 p,float3 w)
    {
        return g_tColor.Sample(TextureFiltering,p.yz).rgb*w.x+g_tColor.Sample(TextureFiltering,p.xz).rgb*w.y+g_tColor.Sample(TextureFiltering,p.xy).rgb*w.z;
    }
    float4 MainPs(PixelInput i):SV_Target0
    {
        Material m=Material::Init(i);
        float3 p=m.WorldPosition,n=normalize(i.vNormalWs);
        float3 w=pow(abs(n),5);w/=max(dot(w,1),.00001);
        float3 rock=Rock(p/700,w)*.58+Rock(p/170,w)*.42;
        float large=N(p.xy/2600)*.55+N(p.xy/680)*.30+N(p.xy/190)*.15;
        float strata=N(float2(p.x*.0004+p.y*.0006,p.z*.005+N(p.xy/900)*2));
        float treeline=1-smoothstep(2600,4800+large*500,p.z);
        float forest=treeline*smoothstep(.38,.80,n.z);
        float snowline=6100+N(p.xy/2700)*1600;
        float snow=smoothstep(snowline,snowline+1700,p.z)*smoothstep(.28,.74,n.z);
        snow*=smoothstep(.30,.73,N(p.xy/210+N(p.xy/1100)*3));
        float3 stone=rock*float3(.83,.86,.89)*lerp(.63,1.18,large)*lerp(.77,1.05,strata);
        float3 woodland=rock*float3(.22,.30,.19)*lerp(.68,1.15,N(p.xy/150));
        m.Albedo=lerp(lerp(stone,woodland,forest*.84),float3(.63,.66,.68),snow*.78);
        float2 bx=g_tNormal.Sample(TextureFiltering,p.yz/390).rg*2-1;
        float2 by=g_tNormal.Sample(TextureFiltering,p.xz/390).rg*2-1;
        float2 bz=g_tNormal.Sample(TextureFiltering,p.xy/390).rg*2-1;
        float3 detail=float3(sign(n.x),bx.x,bx.y)*w.x+float3(by.x,sign(n.y),by.y)*w.y+float3(bz.x,bz.y,sign(n.z))*w.z;
        m.Normal=normalize(lerp(n,normalize(detail),.27*(1-snow)));
        m.Opacity=1;m.Metalness=0;m.Transmission=0;m.Roughness=.91;
        m.AmbientOcclusion=lerp(.72,1,large);
        return ShadingModelStandard::Shade(i,m);
    }
}
