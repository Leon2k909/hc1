HEADER
{
    Description = "Belltower fine flowing jets and ballistic impact droplets";
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
    #define S_TRANSLUCENT 1
    #include "common/shared.hlsl"
    float g_flFlowSpeed < Default(1.3); Range(.1,4); UiGroup("Water"); >;
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
    PixelInput MainVs(VertexInput i)
    {
        PixelInput o = ProcessVertex(i);
        if (o.vTextureCoords.x > 1.5)
        {
            float identity = floor(o.vTextureCoords.x)-2;
            // A 3.25-inch splash height and 0.26-second flight approximate
            // normal gravity; the stream's texture speed is independent.
            float phase = frac(identity*.61803399+g_flTime*3.85);
            float angle = identity*2.39996323;
            // Object axes are world XYZ in the authored, untransformed town mesh.
            i.vPositionOs.xyz += float3(cos(angle)*4*phase,sin(angle)*4*phase,13*phase*(1-phase));
            o = ProcessVertex(i);
        }
        return FinalizeVertex(o);
    }
}
PS
{
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"
    BoolAttribute(DoNotCastShadows,true);
    RenderState(DepthWriteEnable,false);
    RenderState(DepthEnable,true);
    RenderState(BlendEnable,true);
    RenderState(SrcBlend,SRC_ALPHA);
    RenderState(DstBlend,INV_SRC_ALPHA);
    RenderState(CullMode,NONE);
    SamplerState FlowSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    CreateInputTexture2D(NormalA,Linear,8,"","_normal","Water",Default3(.5,.5,1));
    Texture2D g_tNormalA < Channel(RGB,Box(NormalA),Linear); OutputFormat(BC7); SrgbRead(false); >;
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material water = Material::Init(i);
        float2 uv = i.vTextureCoords.xy;
        bool droplet = uv.x > 1.5;
        float3 n = DecodeNormal(g_tNormalA.Sample(FlowSampler,float2(uv.x,uv.y-g_flTime*g_flFlowSpeed*3)).xyz);
        water.Normal = TransformNormal(normalize(float3(n.xy*.43,1)),i.vNormalWs,i.vTangentUWs,i.vTangentVWs);
        water.Albedo = float3(.19,.23,.22);
        water.Roughness = .075;
        water.Metalness = 0;
        water.AmbientOcclusion = 1;
        float3 view = normalize(g_vCameraPositionWs-water.WorldPosition);
        float edge = pow(1-saturate(abs(dot(view,water.Normal))),3);
        float streak = .5+.5*sin(uv.y*11-g_flTime*g_flFlowSpeed*31+.8*sin(uv.x*17));
        water.Opacity = .10+edge*.36+streak*.055;
        if (droplet)
        {
            water.Normal = normalize(i.vNormalWs);
            float identity = floor(uv.x)-2;
            float phase = frac(identity*.61803399+g_flTime*3.85);
            water.Opacity = (.24+edge*.38)*smoothstep(0,.12,phase)*(1-smoothstep(.68,1,phase));
        }
        return ShadingModelStandard::Shade(i,water);
    }
}
