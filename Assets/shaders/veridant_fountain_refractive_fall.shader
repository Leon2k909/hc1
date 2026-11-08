HEADER
{
    Description = "Veridant spillway with advected surface waves and screen-space refraction";
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
    PixelInput MainVs( VertexInput i )
    {
        float2 uv = ProcessVertex(i).vTextureCoords.xy;
        float t = uv.y;
        float lane = cos(uv.x * 6.283185);
        float flow = t * 18 - g_flTime * 39;
        float2 outward = normalize(i.vPositionOs.xy);
        float fold = sin(flow + lane * 4.1) * .15
                   + sin(flow * 1.83 - lane * 9.7) * .08;
        i.vPositionOs.xy += outward * fold * smoothstep(0, .36, t);
        return FinalizeVertex(ProcessVertex(i));
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
    SamplerState FlowSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    SamplerState RefractionSampler < Filter(MIN_MAG_MIP_LINEAR); AddressU(CLAMP); AddressV(CLAMP); >;
    Texture2D g_tFrameBufferCopyTexture < Attribute("FrameBufferCopyTexture"); SrgbRead(false); >;
    CreateInputTexture2D(FlowNormal, Linear, 8, "", "_normal", "Water", Default3(.5,.5,1));
    Texture2D g_tFlowNormal < Channel(RGB, Box(FlowNormal), Linear); OutputFormat(BC7); SrgbRead(false); >;

    float Noise( float2 p )
    {
        float2 cell = floor(p);
        float2 f = frac(p);
        f = f * f * (3 - 2 * f);
        float4 seed = dot(cell, float2(127.1, 311.7)) + float4(0, 127.1, 311.7, 438.8);
        float4 n = frac(sin(seed) * 43758.5453);
        return lerp(lerp(n.x, n.y, f.x), lerp(n.z, n.w, f.x), f.y);
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material water = Material::Init(i);
        float3 world = water.WorldPosition;
        float t = i.vTextureCoords.y;
        float x = cos(i.vTextureCoords.x * 6.283185);
        float flow = t - g_flTime * 2.45;
        float ribbon = Noise(float2(x * 14.1, flow * 4.7));
        float fine = Noise(float2(x * 37.2 + 11, flow * 21.8));
        float strand = ribbon * .68 + fine * .32;
        float edge = smoothstep(.48, 1, abs(x));
        float tear = smoothstep(.34, .95, t + abs(x) * .23) * edge;
        float coverage = lerp(1, smoothstep(.29, .60, strand), tear);
        coverage *= 1 - smoothstep(.9, 1, abs(x) + (fine - .5) * .1);
        float bubbles = smoothstep(.48, .84, strand) * smoothstep(.78, 1, t) * .48;

        float2 broad = DecodeNormal(g_tFlowNormal.Sample(FlowSampler, float2(x * 1.1, flow * 1.4)).xyz).xy;
        float2 narrow = DecodeNormal(g_tFlowNormal.Sample(FlowSampler, float2(x * 2.8 + .3, flow * 2.9)).xyz).xy;
        float2 slope = broad * .36 + narrow * .17;
        slope.x += (ribbon - .5) * .32;
        float3 geometric = normalize(i.vNormalWs);
        water.Normal = TransformNormal(normalize(float3(slope, 1)), geometric, i.vTangentUWs, i.vTangentVWs);
        float3 view = normalize(g_vCameraPositionWs - world);
        float facing = saturate(abs(dot(view, water.Normal)));
        float fresnel = .02037 + .62 * pow(1 - facing, 4);
        float variance = dot(ddx(water.Normal), ddx(water.Normal)) + dot(ddy(water.Normal), ddy(water.Normal));
        water.Roughness = sqrt(.068 * .068 + min(variance * .21, .055)) + bubbles * .16;
        water.Albedo = float3(.44, .51, .49) * bubbles;
        water.Metalness = 0;
        water.AmbientOcclusion = 1;
        water.Opacity = 1;
        CombinerInput ci = ShadingModelStandard::MaterialToCombinerInput(water);
        ci.vSpecularColor = float3(.02037, .02037, .02037);
        ci.vRoughness = water.Roughness.xx;
        LightingTerms_t light = InitLightingTerms();
        ComputeDirectLighting(light, ci);
        float3 ambient = AmbientLight::From(world, i.vPositionSs, water.Normal);
        float3 reflected = EnvMap::From(world, i.vPositionSs, water.Normal, water.Roughness.xx) * fresnel * .7;

        float2 uv = CalculateViewportUv(i.vPositionSs.xy);
        float2 bend = mul(g_matWorldToView, float4(water.Normal - geometric, 0)).xy;
        float2 displaced = saturate(uv + float2(bend.x, -bend.y) * .102 * (1 - bubbles));
        float3 refractedDepth = Depth::GetWorldPosition(displaced / g_vInvViewportSize);
        if (dot(refractedDepth - world, view) > .08)
            displaced = uv;
        float2 bufferScale = g_vFrameBufferCopyInvSizeAndUvScale.zw;
        float3 refracted = g_tFrameBufferCopyTexture.SampleLevel(RefractionSampler, displaced * bufferScale, 0).rgb;
        float opticalOpacity = .075 + fresnel * .24 + bubbles * .26;
        float refraction = (.54 + ribbon * .16) * (1 - opticalOpacity);
        float alpha = (opticalOpacity + refraction) * coverage;
        float3 specular = light.vSpecular.rgb + reflected;
        specular /= 1 + dot(specular, float3(.2126, .7152, .0722)) * 2.8;
        float3 aeration = (light.vDiffuse.rgb + ambient) * ci.vDiffuseColor.rgb;
        float3 lit = (specular + aeration) * coverage;
        float3 fogged = DoAtmospherics(world, i.vPositionSs.xy, float4(lit, alpha)).rgb;
        float3 fog = DoAtmospherics(world, i.vPositionSs.xy, float4(0, 0, 0, 1)).rgb;
        // A soft blue-grey sheen defines the sheet against dark backgrounds.
        // Keep the neutral foam near the impact and avoid hard white streaks.
        float crest = smoothstep(.27, .79, ribbon);
        float rim = smoothstep(.61, .89, abs(x)) * (1 - smoothstep(.90, 1, abs(x)));
        float sheen = .22 + .43 * crest + .28 * rim
                    + .28 * (1 - smoothstep(0, .18, t)) + .39 * smoothstep(.45, .94, t);
        float3 scattered = (float3(.037, .062, .067) * sheen
            + float3(.08, .10, .097) * bubbles) * coverage;
        return float4(max(0, fogged - fog * (1 - alpha)) + refracted * refraction * coverage + scattered, alpha);
    }
}
