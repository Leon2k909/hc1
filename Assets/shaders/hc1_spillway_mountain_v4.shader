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
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
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
        Material m=Material::Init(i);
        float3 p=m.WorldPosition;
        float3 n=normalize(i.vNormalWs);
        float3 weights=pow(abs(n),4);
        weights/=max(dot(weights,1),.00001);
        float3 q=p/640;
        float3 rock=g_tColor.Sample(TextureFiltering,q.yz).rgb*weights.x
                   +g_tColor.Sample(TextureFiltering,q.xz).rgb*weights.y
                   +g_tColor.Sample(TextureFiltering,q.xy).rgb*weights.z;
        float macro=MN(p.xy/2100)*.6+MN(p.xy/450)*.4;
        float snow=smoothstep(9300+macro*2000,12400+macro*2000,p.z)*smoothstep(.4,.85,n.z);
        snow*=smoothstep(.40,.68,MN(p.xy/440+MN(p.xy/1700)*4))*.24;
        float forest=(1-smoothstep(1300,3600,p.z))*smoothstep(.2,.7,n.z);
        float3 stone=rock*g_flTintColor*lerp(.82,1.18,macro);
        stone=lerp(stone,stone*float3(.40,.51,.30),forest*.8);
        m.Albedo=lerp(stone,float3(.22,.25,.28)*lerp(.85,1,macro),snow);
        m.Normal=n;
        m.Opacity=1;m.AmbientOcclusion=1;
        m.Metalness=0;m.Transmission=0;m.Roughness=.92;
        return ShadingModelStandard::Shade(i,m);
    }
}
