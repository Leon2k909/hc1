HEADER
{
    Description = "Forest Base: Aerated cascade: moving surface relief and branching flow";
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
    PixelInput MainVs(VertexInput i)
    {
        PixelInput o=ProcessVertex(i);
        // The existing dense grid carries a few inches of moving relief.
        // Travel is down world Z, independently of imported UV orientation.
        float h=o.vPositionWs.z;
        float u=o.vTextureCoords.x;
        float interior=smoothstep(0,.04,u)*smoothstep(0,.04,1-u);
        float relief=8.0+sin(h*.035+g_flTime*3.2+u*23)*3.5
                    +sin(h*.081+g_flTime*6.6-u*49)*1.5;
        o.vPositionWs+=normalize(o.vNormalWs)*relief*interior;
        // Keep the falling sheet in front of the two recessed rock shelves.
        o.vPositionWs.x-=48*(1-smoothstep(900,1200,h))*interior;
        o.vPositionPs=Position3WsToPs(o.vPositionWs);
        return FinalizeVertex(o);
    }
}
PS
{
    #define BLEND_MODE_ALREADY_SET 1
    RenderState(BlendEnable, true);
    RenderState(SrcBlend, SRC_ALPHA);
    RenderState(DstBlend, INV_SRC_ALPHA);
    RenderState(DepthWriteEnable, false);
    #include "common/pixel.hlsl"
    SamplerState FlowSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    CreateInputTexture2D(FlowMask, Linear, 8, "", "_mask", "Water", Default3(.5,.5,.5));
    Texture2D FlowTexture < Channel(RGB, Box(FlowMask), Linear); OutputFormat(BC7); SrgbRead(false); >;
    float FlowTiling < Default(1); Range(1,12); UiGroup("Water"); >;
    float FlowTop < Default(1200); Range(0,3000); UiGroup("Water"); >;
    float FlowPhase < Default(0); Range(0,1); UiGroup("Water"); >;
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 uvDx=ddx(i.vTextureCoords.xy),uvDy=ddy(i.vTextureCoords.xy);
        float uvDet=uvDx.x*uvDy.y-uvDx.y*uvDy.x;
        float heightAlongV=uvDx.x*ddy(m.WorldPosition.z)-uvDy.x*ddx(m.WorldPosition.z);
        float progress=saturate(heightAlongV*uvDet<0?i.vTextureCoords.y:1-i.vTextureCoords.y);
        float2 uv=float2(i.vTextureCoords.x,progress);
        float flowX=uv.x*FlowTiling;
        float phase=sqrt(max(progress,.005))*2.3-g_flTime*1.32+FlowPhase;
        float3 coarse=FlowTexture.Sample(FlowSampler,float2(flowX*.48,phase*.27)).rgb;
        float bend=(coarse.g-.5)*.13+sin(progress*11+g_flTime*.35)*.015;
        float3 a=FlowTexture.Sample(FlowSampler,float2(flowX*1.45+bend,phase)).rgb;
        float3 b=FlowTexture.Sample(FlowSampler,float2(flowX*3.8-bend,phase*1.19-g_flTime*.16)).rgb;
        float density=saturate(a.r*.63+b.r*.37);
        // One broad falling body, with a dense centre and irregular soft edges.
        // The previous three Gaussian channels exposed large strips of rock.
        float centre=.5+.018*sin(progress*10)+.012*sin(progress*23+1.7);
        float width=lerp(.23,.32,pow(progress,.7));
        float fray=(coarse.r-.5)*.045+(a.g-.5)*.018;
        float distanceFromCentre=abs((uv.x-centre+fray)/width);
        float curtain=1-smoothstep(.72,1.12,distanceFromCentre);
        float core=1-smoothstep(.28,.82,distanceFromCentre);
        float filaments=smoothstep(.18,.72,density);
        float aeration=saturate(.18+filaments*.65+core*.12+progress*.08);
        float tail=smoothstep(-260,-150,m.WorldPosition.z);
        float entry=smoothstep(0,.018,progress);
        float3 tangent=normalize(i.vTangentUWs);
        float3 along=normalize(i.vTangentVWs);
        float3 reliefNormal=normalize(cross(ddx(m.WorldPosition),ddy(m.WorldPosition)));
        if(dot(reliefNormal,m.Normal)<0) reliefNormal=-reliefNormal;
        m.Normal=normalize(lerp(m.Normal,reliefNormal,.7)+tangent*(a.g-b.g)*.20+along*(coarse.b-.5)*.10);
        m.Albedo=lerp(float3(.24,.34,.36),float3(.72,.79,.80),aeration);
        m.Emission=float3(.16,.19,.20)*aeration;
        m.Roughness=lerp(.48,.88,aeration);
        m.Metalness=0;
        m.AmbientOcclusion=1;
        // Keep a continuous translucent water body; detail varies density
        // instead of cutting the fall into see-through threads.
        m.Opacity=curtain*tail*entry*(.70+.27*filaments);
        return ShadingModelStandard::Shade(i,m);
    }
}
