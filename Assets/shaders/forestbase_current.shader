HEADER
{
    Description = "Forest Base: subdued, world-anchored river foam";
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
    SamplerState CurrentSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    CreateInputTexture2D(SplashMask,Linear,8,"","_mask","Water",Default3(0,0,0));
    Texture2D CurrentTexture < Channel(R,Box(SplashMask),Linear); OutputFormat(BC7); SrgbRead(false); >;

    float CurrentHash(float2 p)
    {
        return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);
    }
    float CurrentNoise(float2 p)
    {
        float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(CurrentHash(a),CurrentHash(a+float2(1,0)),f.x),
                    lerp(CurrentHash(a+float2(0,1)),CurrentHash(a+float2(1,1)),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 uv=i.vTextureCoords.xy;
        float edge=smoothstep(0,.18,uv.x)*smoothstep(0,.18,1-uv.x)
                  *smoothstep(0,.22,uv.y)*smoothstep(0,.22,1-uv.y);
        // Engine X is the river's north/south axis. Advect the pattern toward
        // decreasing north; local UVs are used only for a soft mesh boundary.
        float2 p=m.WorldPosition.xy;
        float2 flow=p+float2(g_flTime*18,0);
        float2 warp=float2(CurrentNoise(flow*.004),CurrentNoise(flow*.004+17.3))-.5;
        float2 q=flow*.0025+warp*.35;
        // Independent rotations and nonmatching scales prevent ten copies of
        // one local sprite. Both samples remain filtered and continuous.
        float2 rotated=float2(q.x*.8-q.y*.6,q.x*.6+q.y*.8);
        float a=CurrentTexture.Sample(CurrentSampler,rotated+float2(.23,.61)).r;
        float b=CurrentTexture.Sample(CurrentSampler,float2(-q.y,q.x)*1.37+float2(.71,.13)).r;
        float density=a*.55+b*.45;
        float breakup=smoothstep(.25,.75,CurrentNoise(flow*.006+41.7));
        m.Albedo=float3(.30,.37,.36);
        m.Roughness=.72;
        m.Metalness=0;
        m.AmbientOcclusion=1;
        // This is sparse entrained foam, not the waterfall's bright impact
        // froth. Avoid alpha clipping, which made thin strands blink in motion.
        m.Opacity=saturate(density)*edge*breakup*.14;
        return ShadingModelStandard::Shade(i,m);
    }
}
