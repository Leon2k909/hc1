HEADER
{
    Description = "Spillway alpine backdrop: rock strata, forest floor and snow by height and slope";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth( S_MODE_DEPTH );
    ToolsShadingComplexity( "tools_shading_complexity.shader" );
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float MN(float2 p)
    {
        float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);
        float4 h=frac(sin(float4(dot(a,float2(127.1,311.7)),dot(a+float2(1,0),float2(127.1,311.7)),dot(a+float2(0,1),float2(127.1,311.7)),dot(a+1,float2(127.1,311.7))))*43758.5453);
        return lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
    }
    float4 MainPs(PixelInput i):SV_Target0
    {
        Material m=Material::From(i);
        float3 p=m.WorldPosition;
        float macro=MN(p.xy/2100)*.6+MN(p.xy/450)*.4;
        float snow=smoothstep(8600+macro*1800,11200+macro*1800,p.z)*smoothstep(.3,.85,i.vNormalWs.z);
        snow*=smoothstep(.22,.72,MN(p.xy/650+MN(p.xy/1900)*4))*.75;
        float forest=(1-smoothstep(1300,3600,p.z))*smoothstep(.2,.7,i.vNormalWs.z);
        float3 stone=m.Albedo*lerp(.68,1.1,macro);
        stone=lerp(stone,stone*float3(.40,.51,.30),forest*.8);
        m.Albedo=lerp(stone,float3(.62,.68,.72)*lerp(.85,1,macro),snow);
        m.Metalness=0;m.Transmission=0;m.Roughness=.92;
        return ShadingModelStandard::Shade(i,m);
    }
}
