HEADER
{
    Description = "Belltower clear shallow water with capillary ripples and fine aerated impacts";
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
}
struct VertexInput
{
    #include "common/vertexinput.hlsl"
};
struct PixelInput
{
    #include "common/pixelinput.hlsl"
    float3 vBasinPosition : TEXCOORD8;
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs(VertexInput i)
    {
        PixelInput o = ProcessVertex(i);
        o.vBasinPosition = i.vPositionOs.xyz;
        return FinalizeVertex(o);
    }
}
PS
{
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"
    BoolAttribute(DoNotCastShadows, true);
    BoolAttribute(bWantsFBCopyTexture, true);
    RenderState(DepthWriteEnable, false);
    RenderState(DepthEnable, true);
    RenderState(BlendEnable, true);
    RenderState(SrcBlend, ONE);
    RenderState(DstBlend, INV_SRC_ALPHA);
    RenderState(SrcBlendAlpha, ONE);
    RenderState(DstBlendAlpha, INV_SRC_ALPHA);
    RenderState(CullMode, NONE);
    SamplerState FlowSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    SamplerState RefractionSampler < Filter(MIN_MAG_MIP_LINEAR); AddressU(CLAMP); AddressV(CLAMP); >;
    Texture2D g_tFrameBufferCopyTexture < Attribute("FrameBufferCopyTexture"); SrgbRead(false); >;
    CreateInputTexture2D(NormalA, Linear, 8, "", "_normal", "Water", Default3(.5,.5,1));
    CreateInputTexture2D(NormalB, Linear, 8, "", "_normal", "Water", Default3(.5,.5,1));
    Texture2D g_tNormalA < Channel(RGB, Box(NormalA), Linear); OutputFormat(BC7); SrgbRead(false); >;
    Texture2D g_tNormalB < Channel(RGB, Box(NormalB), Linear); OutputFormat(BC7); SrgbRead(false); >;
    float3 g_vBasinCentre < Default3(130,0,21.5); UiGroup("Water"); >;
    float3 g_vWaterColor < UiType(Color); Default3(.035,.085,.073); UiGroup("Water"); >;
    float g_flAbsorptionDistance < Default(95); Range(40,500); UiGroup("Water"); >;
    float g_flWaterRoughness < Default(.085); Range(.04,.4); UiGroup("Water"); >;

    float FountainHash21(float2 p)
    {
        return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);
    }
    float FountainNoise(float2 p)
    {
        float2 cell=floor(p);
        float2 f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(FountainHash21(cell),FountainHash21(cell+float2(1,0)),f.x),
                    lerp(FountainHash21(cell+float2(0,1)),FountainHash21(cell+1),f.x),f.y);
    }
    float3 Impact(float2 delta,float phase)
    {
        float2 drift=.14*float2(sin(g_flTime*4.3+phase),cos(g_flTime*3.7+phase));
        float2 p=delta+drift;
        float radius=length(p);
        // Impacts are over 100 inches apart. Avoid evaluating the other three
        // spray/noise fields for every basin pixel, and fade the cutoff fully.
        if(radius>=36) return float3(0,0,0);
        float angle=atan2(p.y,p.x);
        float envelope=exp(-radius/10)*smoothstep(.6,2.0,radius)*(1-smoothstep(28,36,radius));
        float waviness=.31*sin(angle*3+phase)+.19*sin(angle*7-g_flTime*.8)
                      +.65*(FountainNoise(p*.65+phase+g_flTime*.13)-.5);
        float wave=radius*1.85-g_flTime*9.2+phase+waviness;
        float resolved=1-smoothstep(.55,1.6,fwidth(radius)*1.85);
        float2 slope=p/max(radius,.08)*(cos(wave)+.28*cos(wave*1.71+phase))*envelope*.10*resolved;
        float aeration=0;
        if(radius<7)
        {
        float boil=exp(-radius*radius/7.0);
        slope+=float2(FountainNoise(p*2.5+float2(g_flTime*1.4,phase))-.5,
                      FountainNoise(p*2.9+float2(phase,-g_flTime*1.7))-.5)*boil*.42;
        // Aeration is concentrated at the actual strike. Two advected scales
        // break its edge into short-lived fragments instead of stamped rings.
        float2 flow=float2(g_flTime*.63,-g_flTime*.41);
        float2 warp=float2(FountainNoise(p*.91+flow*.31+phase),
                           FountainNoise(p*.83-flow*.27-phase));
        float2 q=float2(.8*p.x+.6*p.y,-.6*p.x+.8*p.y)+(warp-.5)*1.9;
        q+=.09*float2(sin(p.y*2.7+g_flTime),cos(p.x*3.1-g_flTime));
        float coarse=FountainNoise(q*4.7+flow+phase);
        float fine=FountainNoise(q*9.1-flow*1.4-phase);
        float foam=smoothstep(.38,.70,coarse*.65+fine*.35);
        aeration=exp(-radius*radius/1.6)*foam;
        }
        float crest=pow(.5+.5*cos(wave),18)*envelope*resolved;
        float broken=smoothstep(.30,.75,FountainNoise(p*1.1+phase+g_flTime*.18));
        float bubbles=aeration*.20+crest*broken*.065;
        return float3(slope,bubbles);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material water = Material::Init(i);
        float3 world = water.WorldPosition;
        float2 p = i.vBasinPosition.xy-g_vBasinCentre.xy;
        float3 a = DecodeNormal(g_tNormalA.Sample(FlowSampler, p/44+float2(.013,-.018)*g_flTime).xyz);
        float3 b = DecodeNormal(g_tNormalB.Sample(FlowSampler, p/29+float2(-.017,.011)*g_flTime).xyz);
        float3 impact = Impact(p-float2(72,0), .2)+Impact(p+float2(72,0), 1.7)
                      + Impact(p-float2(0,72), 3.1)+Impact(p+float2(0,72), 4.5);
        float2 quiet = float2(cos(dot(p,float2(.08,.043))-g_flTime*.8),
                             sin(dot(p,float2(-.05,.077))+g_flTime*.63))*.028;
        water.Normal = normalize(float3(a.xy*.40+b.xy*.28+quiet+impact.xy,1));
        water.Roughness = g_flWaterRoughness+impact.z*.12;
        water.Metalness = 0;
        water.AmbientOcclusion = 1;
        float3 bed = Depth::GetWorldPosition(i.vPositionSs.xy);
        float depth = max(0, world.z-bed.z);
        float contact = smoothstep(0,.8,depth);
        float path = min(length(world-bed),96);
        // A slight green cast comes from unequal absorption through the actual
        // water path, rather than a constant blue surface opacity.
        float3 transmission = exp(-path*float3(1.6,.78,1.0)/max(g_flAbsorptionDistance,1));
        float3 view = g_matViewToProjection[3].w != 0 ? -g_vCameraDirWs : normalize(g_vCameraPositionWs-world);
        float ndotv = saturate(abs(dot(view,water.Normal)));
        const float f0 = .02037;
        float fresnel = saturate(CalcBRDFReflectionFactor(ndotv,water.Roughness,f0).x);
        float foam = saturate(impact.z*.22);
        float3 through = transmission*(1-fresnel);
        float minimumThrough = min(through.x,min(through.y,through.z));
        // Preserve spray already drawn into this translucent layer. Refraction
        // is a colour delta, so the basin does not overwrite the falling jet.
        water.Opacity = 1-minimumThrough;
        water.Albedo = g_vWaterColor*(1-transmission)+float3(.55,.58,.55)*foam;
        CombinerInput ci = ShadingModelStandard::MaterialToCombinerInput(water);
        ci.vSpecularColor = f0.xxx;
        ci.vRoughness = water.Roughness.xx;
        LightingTerms_t light = InitLightingTerms();
        ComputeDirectLighting(light,ci);
        float3 ambient = AmbientLight::From(world,i.vPositionSs,water.Normal);
        float3 reflection = EnvMap::From(world,i.vPositionSs,water.Normal,water.Roughness.xx)
                          * CalcBRDFReflectionFactor(ndotv,water.Roughness,ci.vSpecularColor);
        float2 screen = CalculateViewportUv(i.vPositionSs.xy);
        float2 wobble = mul(g_matWorldToView,float4(water.Normal-float3(0,0,1),0)).xy*.007*saturate(depth/18);
        float2 displaced = saturate(screen+float2(wobble.x,-wobble.y));
        float3 shiftedBed = Depth::GetWorldPosition(displaced/g_vInvViewportSize);
        if(shiftedBed.z > world.z-.05) displaced=screen;
        float2 bufferUv = displaced*g_vFrameBufferCopyInvSizeAndUvScale.zw;
        float3 behind = g_tFrameBufferCopyTexture.SampleLevel(RefractionSampler,bufferUv,0).rgb;
        float3 originalBehind = g_tFrameBufferCopyTexture.SampleLevel(RefractionSampler,
                                screen*g_vFrameBufferCopyInvSizeAndUvScale.zw,0).rgb;
        float3 refracted = behind*max(through-minimumThrough.xxx,0)
                         +(behind-originalBehind)*minimumThrough*.55;
        float3 lit = (light.vDiffuse.rgb+ambient)*ci.vDiffuseColor.rgb + light.vSpecular.rgb + reflection + refracted;
        lit+=(ambient+float3(.30,.34,.35))*impact.z*.60;
        float4 colour = DoAtmospherics(world,i.vPositionSs.xy,float4(lit,water.Opacity));
        float3 fog = DoAtmospherics(world,i.vPositionSs.xy,float4(0,0,0,1)).rgb;
        colour.rgb = max(0,colour.rgb-fog*(1-water.Opacity))*contact;
        colour.a *= contact;
        return colour;
    }
}
