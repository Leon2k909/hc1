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
        float relief=sin(h*.035+g_flTime*3.2+u*23)*3.5
                    +sin(h*.081+g_flTime*6.6-u*49)*1.7;
        o.vPositionWs+=normalize(o.vNormalWs)*relief*interior;
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
        // Shared UV progress follows the whole connected cascade, including its
        // ledges. A decreasing phase advects features toward increasing v.
        float2 uvDx=ddx(i.vTextureCoords.xy),uvDy=ddy(i.vTextureCoords.xy);
        float uvDet=uvDx.x*uvDy.y-uvDx.y*uvDy.x;
        float heightAlongV=uvDx.x*ddy(m.WorldPosition.z)-uvDy.x*ddx(m.WorldPosition.z);
        // Recover V orientation from the actual height gradient, so importer
        // V flips cannot reverse the flow or put the entry fade at the foot.
        float progress=saturate(heightAlongV*uvDet<0?i.vTextureCoords.y:1-i.vTextureCoords.y);
        float2 uv=float2(i.vTextureCoords.x,progress);
        float flowX=uv.x*FlowTiling;
        // Moving towards increasing v sends the pattern down the authored fall.
        // The nonlinear spatial phase makes filaments stretch as they descend.
        float phase=sqrt(max(uv.y,.005))*5.8-g_flTime*1.32+FlowPhase;
        float drift=sin(uv.y*11+g_flTime*.65+FlowPhase*9)*.012;
        float3 coarse=FlowTexture.Sample(FlowSampler,float2(flowX*.55+FlowPhase,phase*.30)).rgb;
        float bend=(coarse.g-.5)*.12+drift;
        float3 a=FlowTexture.Sample(FlowSampler,float2(flowX*2.2+bend,phase)).rgb;
        float3 b=FlowTexture.Sample(FlowSampler,float2(flowX*5.4-bend,phase*1.21-g_flTime*.17)).rgb;
        float density=lerp(a.r,b.r,.34)*lerp(.70,1.17,coarse.r);
        // Persistent, unequal channels expose wet cliff between the falling
        // ribbons. They meander spatially; only the fine froth travels rapidly.
        float channelX=uv.x+.022*sin(progress*12)+.014*sin(progress*29+1.7);
        float3 centres=float3(.15,.49,.82)+sin(progress*float3(17,11,23)+float3(1.3,3.9,2.1))
                         *float3(.018,.028,.016);
        float3 widths=float3(.145,.19,.125)*
                       (1+sin(progress*float3(23,15,19)+float3(.7,2.4,4.1))*float3(.23,.18,.28));
        // Unequal channels split and reconnect along the rock. Their moving
        // edges share the same advected texture as the froth in the core.
        float channelXFrayed=channelX+(coarse.g-.5)*.032;
        float3 channelD=(channelXFrayed-centres)/widths;
        float3 channelShape=exp(-channelD*channelD*2.2);
        float channel=saturate(channelShape.x+channelShape.y+channelShape.z);
        float core=saturate(max(channelShape.x,max(channelShape.y,channelShape.z)));
        channel*=lerp(.8,1.0,smoothstep(.0,.25,progress));
        float aeration=saturate(smoothstep(.20,.67,density)*.60+core*core*.40);
        float foam=saturate(aeration*channel*(.65+.30*progress));
        float fray=.014*sin(uv.y*19+g_flTime*.48+FlowPhase*9)+.012*(coarse.r-.5);
        float edge=smoothstep(0,.04,uv.x+drift-fray)*smoothstep(0,.04,1-uv.x-drift-fray);
        // Fade in the spray above the opaque pool's depth intersection. A
        // fade only at the submerged mesh end was hidden beneath the pool.
        float tail=smoothstep(-255,-110,m.WorldPosition.z);
        // Preserve the surface orientation where water rolls across a ledge.
        // Rough, aerated foam softens its response without a fixed vertical normal.
        float3 tangent=normalize(i.vTangentUWs);
        float3 along=normalize(i.vTangentVWs);
        m.Normal=normalize(m.Normal+tangent*(a.g-b.g)*.22+along*(coarse.b-.5)*.12);
        // Multiple scattering inside aerated water softens the cliff's
        // triangulated shadow silhouette. The existing standard shader still
        // supplies fog and tonemapping, while the froth is diffusely luminous.
        m.Albedo=lerp(float3(.045,.06,.07),float3(.38,.41,.42),foam);
        m.Emission=lerp(float3(.012,.017,.022),float3(.32,.355,.38),foam);
        m.Roughness=lerp(.28,.90,foam);
        m.Metalness=0;
        m.AmbientOcclusion=1;
        // Fine filaments interrupt the silhouette instead of reading as a
        // solid rectangular curtain. Dark water remains on the wet rock.
        float strands=smoothstep(.24,.76,density);
        float entry=smoothstep(0,.02,uv.y);
        m.Opacity=edge*tail*entry*(.025+channel*(.12+core*.16+strands*(.50+.22*progress)));
        clip(m.Opacity-.025);
        return ShadingModelStandard::Shade(i,m);
    }
}
