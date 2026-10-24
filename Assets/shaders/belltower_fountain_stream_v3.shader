HEADER
{
    Description = "Belltower flowing clear jets, rounded breakup beads and fine impact spray";
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
    float g_flFlowSpeed < Default(1); Range(.1,4); UiGroup("Water"); >;
    float3 g_vBasinCentre < Default3(130,0,21.5); UiGroup("Water"); >;
    float FountainHash(float x) { return frac(sin(x*127.1+311.7)*43758.5453); }
    float2 SpoutDirection(float2 delta)
    {
        return abs(delta.x)>abs(delta.y) ? float2(sign(delta.x),0) : float2(0,sign(delta.y));
    }
}
struct VertexInput
{
    #include "common/vertexinput.hlsl"
};
struct PixelInput
{
    #include "common/pixelinput.hlsl"
    #if ( PROGRAM == VFX_PROGRAM_PS )
        bool bIsFrontface : SV_IsFrontFace;
    #endif
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs(VertexInput i)
    {
        PixelInput o=ProcessVertex(i);
        float2 uv=o.vTextureCoords.xy;
        float2 outward=SpoutDirection(i.vPositionOs.xy-g_vBasinCentre.xy);
        float2 impact=g_vBasinCentre.xy+outward*72;
        if(uv.x>1.5)
        {
            float identity=floor(uv.x)-2;
            if(identity>=128)
            {
                float phase=frac(identity*.61803399+g_flTime*3.07);
                float t=.80+.20*phase;
                float3 centre=float3(g_vBasinCentre.xy+outward*(37.12+34.88*t),42-20.5*t*t);
                i.vPositionOs.xyz+=centre-float3(impact,21.5);
            }
            else
            {
                // Different flight times, angles and launch velocities keep a
                // steady jet's spray irregular while retaining normal gravity.
                float flight=lerp(.12,.24,FountainHash(identity+4));
                float phase=frac(identity*.61803399+g_flTime/flight);
                float age=phase*flight;
                float angle=identity*2.39996323;
                float speed=lerp(11,29,FountainHash(identity+17));
                float vertical=386.1*flight*.5;
                i.vPositionOs.xyz+=float3(float2(cos(angle),sin(angle))*speed*age,
                                         .05+vertical*age-193.05*age*age);
            }
        }
        else if(uv.x< -1.5)
        {
            float identity=floor(-uv.x)-2;
            float phase=frac(identity*.61803399+g_flTime*4.1);
            float burst=sin(phase*3.14159265);
            i.vPositionOs.xy=impact+(i.vPositionOs.xy-impact)*lerp(.3,1,phase);
            i.vPositionOs.z=21.5+(i.vPositionOs.z-21.5)*burst;
        }
        else
        {
            float t=saturate(uv.y/5.6);
            float3 centre=float3(g_vBasinCentre.xy+outward*(37.12+34.88*t),42-20.5*t*t);
            float3 radial=i.vPositionOs.xyz-centre;
            float motion=g_flTime*g_flFlowSpeed;
            float pulse=sin(t*91-motion*43)+.42*sin(t*157-motion*67);
            i.vPositionOs.xyz=centre+radial*(1+.072*pulse*smoothstep(.02,.8,t));
            float2 sideways=float2(-outward.y,outward.x);
            i.vPositionOs.xy+=sideways*(.026*sin(t*39-motion*22)*t*t);
            i.vPositionOs.z+=.022*sin(t*61-motion*30)*t*t;
        }
        o=ProcessVertex(i);
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
        Material water=Material::Init(i);
        float2 uv=i.vTextureCoords.xy;
        bool droplet=uv.x>1.5;
        bool sheet=uv.x< -1.5;
        if((droplet||sheet)&&!i.bIsFrontface) discard;
        float t=saturate(uv.y/5.6);
        float3 n=DecodeNormal(g_tNormalA.Sample(FlowSampler,float2(uv.x*1.7,uv.y*1.6-g_flTime*g_flFlowSpeed*3.4)).xyz);
        water.Normal=droplet ? normalize(i.vNormalWs)
            : TransformNormal(normalize(float3(n.xy*(sheet?.16:.20),1)),i.vNormalWs,i.vTangentUWs,i.vTangentVWs);
        if(!i.bIsFrontface) water.Normal=-water.Normal;
        water.Albedo=float3(.002,.003,.003);
        water.Roughness=sheet?.075:.055;
        water.Metalness=0;
        water.AmbientOcclusion=1;
        float3 view=normalize(g_vCameraPositionWs-water.WorldPosition);
        float ndotv=saturate(abs(dot(view,water.Normal)));
        float visibility=.82;
        if(droplet)
        {
            float identity=floor(uv.x)-2;
            float flight=lerp(.12,.24,FountainHash(identity+4));
            float phase=frac(identity*.61803399+g_flTime/(identity>=128 ? 1/3.07:flight));
            visibility=smoothstep(0,.07,phase)*(1-smoothstep(.75,1,phase));
            if(identity>=128) visibility*=.42;
        }
        else if(sheet)
        {
            float identity=floor(-uv.x)-2;
            float phase=frac(identity*.61803399+g_flTime*4.1);
            float width=frac(-uv.x);
            float feather=smoothstep(.2,.35,width)*(1-smoothstep(.65,.8,width));
            visibility=.68*feather*smoothstep(0,.10,phase)*(1-smoothstep(.58,1,phase));
        }
        else
        {
            float pulse=.5+.5*sin(uv.y*23-g_flTime*g_flFlowSpeed*43);
            visibility*=lerp(1,lerp(.30,.90,pulse),smoothstep(.67,1,t));
        }
        float edge=pow(1-ndotv,3);
        float movingGlint=pow(.5+.5*sin(uv.x*6.283185+.32*sin(uv.y*8-g_flTime*11)+n.x*.7),12);
        movingGlint*=.35+.65*(.5+.5*sin(uv.y*13-g_flTime*19+n.y*4));
        water.Albedo=float3(.055,.075,.08);
        water.Emission=float3(.64,.74,.78)*movingGlint+float3(.10,.13,.14)*edge;
        water.Opacity=visibility*(.045+edge*.16+movingGlint*.48)*.65;
        if(droplet)
        {
            water.Albedo=float3(.12,.16,.17);
            water.Emission=float3(.75,.84,.88)*(.20+.80*sqrt(edge));
            water.Opacity=visibility*(.20+.60*sqrt(edge));
        }
        else if(sheet)
        {
            water.Albedo=float3(.16,.19,.20);
            water.Emission=float3(.45,.53,.56);
            water.Opacity=visibility*.65;
        }
        return ShadingModelStandard::Shade(i,water);
    }
}
