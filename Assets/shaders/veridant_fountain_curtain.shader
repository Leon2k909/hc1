HEADER
{
    Description = "Thin fountain curtain with accelerating rivulets and perforated edges";
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
    #include "common/shared.hlsl"
    float g_flParcelMotion < Default(0); Range(0, 1); UiGroup("Water"); >;
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
        if (g_flParcelMotion > .5)
        {
            float age = sqrt(saturate((48.45 - i.vPositionOs.z) / 30.95));
            float2 radial = normalize(i.vPositionOs.xy);
            float2 side = float2(-radial.y, radial.x);
            float parcel = age - g_flTime * 2.45;
            float lane = dot(i.vPositionOs.xy, float2(.73, .41));
            float pulse = sin(parcel * 36 + lane) * .64 + sin(parcel * 61 - lane * .7) * .36;
            float breakup = smoothstep(.18, .83, age);
            i.vPositionOs.xy += (side * pulse * .36 + radial * sin(parcel * 24 + lane) * .22) * breakup;
            i.vPositionOs.xyz += i.vNormalOs.xyz * (pulse * .13 * breakup);
        }
        return FinalizeVertex( ProcessVertex( i ) );
    }
}
PS
{
    #define S_TRANSLUCENT 1
    #define BLEND_MODE_ALREADY_SET 1
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( DepthWriteEnable, false );
    #include "common/pixel.hlsl"
    float g_flLipFade < Default(0); Range(0, 1); UiGroup("Water"); >;
    float g_flFullSheet < Default(0); Range(0, 1); UiGroup("Water"); >;

    float WaterNoise( float2 p )
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
        Material m = Material::Init(i);
        float2 uv = i.vTextureCoords.xy;
        float across = cos(uv.x * 6.283185);
        float t = uv.y;
        float phase = (sqrt(t + .09) - .3) * 8 - g_flTime * 4.2;
        float ribbon = WaterNoise(float2(across * 17, phase));
        float bead = WaterNoise(float2(across * 29 + 31, phase * 3.1));
        float foam = smoothstep(.48, .88, ribbon * .67 + bead * .33);
        float breakup = smoothstep(.35, .72, ribbon * .78 + bead * .22);
        float tear = smoothstep(.31, .94, t + abs(across) * .18);
        float fade = lerp(1, breakup, tear);
        float3 normal = normalize(float3((ribbon - .5) * .19, (bead - .5) * .11, 1));
        m.Normal = TransformNormal(normal, i.vNormalWs, i.vTangentUWs, i.vTangentVWs);
        float facing = abs(dot(normalize(-i.vPositionWithOffsetWs), m.Normal));
        float glint = pow(1 - saturate(facing), 3);
        float aeration = foam * lerp(1, .27 + .15 * smoothstep(.76, 1, t), g_flFullSheet);
        m.Albedo = lerp(float3(.13, .20, .20), float3(.83, .88, .86), aeration);
        m.Roughness = lerp(.075, .19, max(g_flFullSheet, g_flParcelMotion)) + foam * .16;
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        float lip = lerp(1, 1 - smoothstep(.32, .96, t), g_flLipFade);
        float neck = smoothstep(.21, .49, WaterNoise(float2(m.WorldPosition.x * .25, phase * 1.7)));
        float parcels = lerp(1, neck, g_flParcelMotion * smoothstep(.22, .78, t));
        float brokenOpacity = (.16 + foam * .57 + glint * .24) * fade * lip * parcels;
        // The centre carries most of the flow. Breakup opens gaps at the sides.
        float edge = smoothstep(.56, .99, abs(across));
        float core = .34 + ribbon * .085 + aeration * .10 + glint * .045;
        float sheetOpacity = lerp(core, brokenOpacity, edge) * (1 - smoothstep(.97, 1.03, abs(across)));
        m.Opacity = lerp(brokenOpacity * lerp(1, .57, g_flParcelMotion), sheetOpacity, g_flFullSheet);
        float4 lit = ShadingModelStandard::Shade(i, m);
        float luminance = dot(lit.rgb, float3(.2126, .7152, .0722));
        lit.rgb /= 1 + max(0, luminance - .18) * 2.1 * max(g_flFullSheet, g_flParcelMotion);
        return lit;
    }
}
