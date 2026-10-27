HEADER
{
    Description = "Veridant shallow reflecting water with filtered ripples and depth-correct refraction";
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
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs(VertexInput input) { return FinalizeVertex(ProcessVertex(input)); }
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
    float3 g_vWaterColor < UiType(Color); Default3(.035,.085,.073); UiGroup("Water"); >;
    float g_flAbsorptionDistance < Default(95); Range(40,500); UiGroup("Water"); >;
    float g_flWaterRoughness < Default(.065); Range(.04,.4); UiGroup("Water"); >;
    float g_flReflectionStrength < Default(.10); Range(0,1); UiGroup("Water"); >;

    float4 MainPs(PixelInput input) : SV_Target0
    {
        Material water = Material::Init(input);
        float3 world = water.WorldPosition;
        float2 p = world.xy;
        float3 a = DecodeNormal(g_tNormalA.Sample(FlowSampler,p/56+float2(.004,-.006)*g_flTime).xyz);
        float3 b = DecodeNormal(g_tNormalB.Sample(FlowSampler,p/37+float2(-.005,.003)*g_flTime).xyz);
        float2 quiet = float2(cos(dot(p,float2(.11,.053))-g_flTime*.70),
                             sin(dot(p,float2(-.067,.097))+g_flTime*.51))*.022;
        water.Normal = normalize(float3(a.xy*.18+b.xy*.13+quiet,1));
        // Derivative variance softens unresolved fine ripples instead of shimmering.
        float variance = dot(ddx(water.Normal),ddx(water.Normal))+dot(ddy(water.Normal),ddy(water.Normal));
        water.Roughness = sqrt(g_flWaterRoughness*g_flWaterRoughness+min(variance*.3,.025));
        water.Metalness = 0;
        water.AmbientOcclusion = 1;
        float3 bed = Depth::GetWorldPosition(input.vPositionSs.xy);
        float depth = max(0,world.z-bed.z);
        float contact = smoothstep(0,.55,depth);
        float path = min(length(world-bed),160);
        float3 transmission = exp(-path*float3(1.4,.78,.92)/max(g_flAbsorptionDistance,1));
        float3 view = g_matViewToProjection[3].w != 0 ? -g_vCameraDirWs : normalize(g_vCameraPositionWs-world);
        float ndotv = saturate(abs(dot(view,water.Normal)));
        const float f0 = .02037;
        float fresnel = saturate(CalcBRDFReflectionFactor(ndotv,water.Roughness,f0).x);
        float3 through = transmission*(1-fresnel);
        float minimumThrough = min(through.x,min(through.y,through.z));
        water.Opacity = 1-minimumThrough;
        water.Albedo = g_vWaterColor*(1-transmission);
        CombinerInput ci = ShadingModelStandard::MaterialToCombinerInput(water);
        ci.vSpecularColor = f0.xxx;
        ci.vRoughness = water.Roughness.xx;
        LightingTerms_t lighting = InitLightingTerms();
        ComputeDirectLighting(lighting,ci);
        float3 ambient = AmbientLight::From(world,input.vPositionSs,water.Normal);
        // Keep the courtyard's strongly coloured local probe subordinate to
        // shallow transmission; direct light reflections retain full energy.
        float3 reflection = EnvMap::From(world,input.vPositionSs,water.Normal,water.Roughness.xx)
                          * CalcBRDFReflectionFactor(ndotv,water.Roughness,ci.vSpecularColor)
                          * g_flReflectionStrength;
        float2 screen = CalculateViewportUv(input.vPositionSs.xy);
        float2 wobble = mul(g_matWorldToView,float4(water.Normal-float3(0,0,1),0)).xy*.017*saturate(depth/12);
        float2 displaced = saturate(screen+float2(wobble.x,-wobble.y));
        float3 shiftedBed = Depth::GetWorldPosition(displaced/g_vInvViewportSize);
        // Refraction may not pull the dry coping or exposed rocks into the pool.
        if(shiftedBed.z > world.z-.05) displaced=screen;
        float2 bufferUv = displaced*g_vFrameBufferCopyInvSizeAndUvScale.zw;
        float3 behind = g_tFrameBufferCopyTexture.SampleLevel(RefractionSampler,bufferUv,0).rgb;
        float3 originalBehind = g_tFrameBufferCopyTexture.SampleLevel(RefractionSampler,
                                screen*g_vFrameBufferCopyInvSizeAndUvScale.zw,0).rgb;
        float3 refracted = behind*max(through-minimumThrough.xxx,0)
                         +(behind-originalBehind)*minimumThrough;
        float3 lit = (lighting.vDiffuse.rgb+ambient)*ci.vDiffuseColor.rgb
                   + lighting.vSpecular.rgb+reflection+refracted;
        float4 colour = DoAtmospherics(world,input.vPositionSs.xy,float4(lit,water.Opacity));
        float3 fog = DoAtmospherics(world,input.vPositionSs.xy,float4(0,0,0,1)).rgb;
        colour.rgb = max(0,colour.rgb-fog*(1-water.Opacity))*contact;
        colour.a *= contact;
        return colour;
    }
}
