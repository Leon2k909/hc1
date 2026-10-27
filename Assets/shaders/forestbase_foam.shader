HEADER
{
    Description = "Forest Base: drifting impact froth and local waterfall spray";
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
    #define S_TRANSLUCENT 1
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
    #define BLEND_MODE_ALREADY_SET 1
    RenderState(BlendEnable,true);
    RenderState(SrcBlend,SRC_ALPHA);
    RenderState(DstBlend,INV_SRC_ALPHA);
    RenderState(DepthWriteEnable,false);
    #include "common/pixel.hlsl"
    SamplerState FoamSampler < Filter(ANISO); AddressU(CLAMP); AddressV(CLAMP); >;
    SamplerState FlowSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    CreateInputTexture2D(SplashMask,Linear,8,"","_mask","Water",Default3(0,0,0));
    Texture2D FoamTexture < Channel(R,Box(SplashMask),Linear); OutputFormat(BC7); SrgbRead(false); >;
    float EllipticalFootprint < Default(0); Range(0,1); UiGroup("Water"); >;
    float ConstrainPlungeBasin < Default(0); Range(0,1); UiGroup("Water"); >;
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 uv=i.vTextureCoords.xy;
        float2 offset=float2(sin(uv.y*19+g_flTime*.71),cos(uv.x*23-g_flTime*.93))*.022;
        float edge=smoothstep(0,.10,uv.x)*smoothstep(0,.10,1-uv.x)*smoothstep(0,.13,uv.y)*smoothstep(0,.13,1-uv.y);
        edge*=lerp(1,1-smoothstep(.60,1,length((uv-.5)*2)),EllipticalFootprint);
        float basin=length((float2(-m.WorldPosition.y,m.WorldPosition.x)-float2(430,3370))/float2(530,440));
        edge*=lerp(1,1-smoothstep(.78,1,basin),ConstrainPlungeBasin);
        float mask=FoamTexture.Sample(FoamSampler,uv+offset).r;
        float a=FoamTexture.Sample(FlowSampler,float2(uv.x+offset.x,uv.y+g_flTime*.085)).r;
        float b=FoamTexture.Sample(FlowSampler,float2(uv.x-offset.x+.31,uv.y+g_flTime*.069+.5)).r;
        mask=lerp(mask,max(a,b)*edge,.65);
        // Every phase must fade at the sprite boundary. Previously the
        // stationary contribution left visible rectangular foam footprints.
        mask*=edge;
        m.Albedo=float3(.72,.78,.80);
        m.Roughness=.34;
        m.Metalness=0;
        m.AmbientOcclusion=1;
        m.Opacity=mask*(.86+.14*sin(uv.x*53+uv.y*79-g_flTime*1.7));
        clip(m.Opacity-.015);
        return ShadingModelStandard::Shade(i,m);
    }
}
