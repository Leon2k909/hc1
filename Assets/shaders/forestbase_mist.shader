HEADER
{
    Description = "Forest Base softly illuminated waterfall impact mist";
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
    float MistStrength < UiType(Slider); Default(1); Range(0,4); UiGroup("Water"); >;
    float ConstrainPlungeBasin < Default(0); Range(0,1); UiGroup("Water"); >;
    SamplerState MistSampler < Filter(ANISO); AddressU(CLAMP); AddressV(CLAMP); >;
    SamplerState DetailSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    CreateInputTexture2D(SplashMask,Linear,8,"","_mask","Water",Default3(0,0,0));
    Texture2D MistTexture < Channel(R,Box(SplashMask),Linear); OutputFormat(BC7); SrgbRead(false); >;
    float MistDepthFeather < Default(28); Range(0,128); UiGroup("Water"); >;
    #include "common/classes/Depth.hlsl"
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 uv=i.vTextureCoords.xy;
        float phase=dot(m.WorldPosition.xy,float2(.0017,.0021));
        float2 drift=float2(sin(g_flTime*.35+uv.y*9+phase),cos(g_flTime*.27+uv.x*8+phase))*.025;
        float edge=smoothstep(0,.12,uv.x)*smoothstep(0,.12,1-uv.x)*smoothstep(0,.1,uv.y)*smoothstep(0,.1,1-uv.y);
        edge*=1-smoothstep(.62,1,length((uv-.5)*2));
        float basin=length((float2(-m.WorldPosition.y,m.WorldPosition.x)-float2(430,3370))/float2(530,440));
        float foot=1-smoothstep(50,250,m.WorldPosition.z);
        edge*=lerp(1,1-smoothstep(.78,1,basin),ConstrainPlungeBasin*foot);
        m.Albedo=0;
        float coarse=MistTexture.Sample(DetailSampler,uv*2.3+float2(-g_flTime*.031,g_flTime*.046)+phase).r;
        float detail=MistTexture.Sample(DetailSampler,uv*5.7+float2(g_flTime*.045,g_flTime*.067)+phase*.71).r;
        float wisps=.4+.6*smoothstep(.018,.11,coarse*.7+detail*.3);
        m.Emission=float3(.30,.35,.38);
        m.Roughness=1;
        m.Metalness=0;
        float density=max(0,MistTexture.Sample(MistSampler,uv+drift).r*edge*MistStrength*wisps);
        m.Opacity=1-exp(-density*1.8);
        // Match the engine sprite soft-intersection path at opaque water and rock.
        float3 depthPosition=Depth::GetWorldPosition(m.ScreenPosition.xy);
        m.Opacity*=saturate(distance(depthPosition,m.WorldPosition)/max(MistDepthFeather,.001));
        return ShadingModelStandard::Shade(i,m);
    }
}
