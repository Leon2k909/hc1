HEADER
{
    Description = "Shallow flowing river with depth-faded banks";
}
MODES
{
    VrForward();
}
FEATURES
{
    #include "common/features.hlsl"
}
COMMON
{
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/pixel.hlsl"
    BoolAttribute( translucent, true );
    RenderState( DepthWriteEnable, false );
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( CullMode, NONE );

    SamplerState g_sFlow < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); >;
    CreateInputTexture2D( NormalA, Linear, 8, "", "_normal", "Water", Default3(.5,.5,1) );
    CreateInputTexture2D( NormalB, Linear, 8, "", "_normal", "Water", Default3(.5,.5,1) );
    Texture2D g_tNormalA < Channel(RGB, Box(NormalA), Linear); OutputFormat(BC7); SrgbRead(false); >;
    Texture2D g_tNormalB < Channel(RGB, Box(NormalB), Linear); OutputFormat(BC7); SrgbRead(false); >;
    float3 g_vWaterColor < UiType(Color); Default3(.055,.15,.13); UiGroup("Water"); >;
    float g_flFlowSpeed < Default(.12); Range(0,1); UiGroup("Water"); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float2 uv = i.vTextureCoords.xy;
        float3 a = DecodeNormal(g_tNormalA.Sample(g_sFlow, uv + float2(.014, -g_flFlowSpeed) * g_flTime).xyz);
        float3 b = DecodeNormal(g_tNormalB.Sample(g_sFlow, uv * 1.71 + float2(-.021, -g_flFlowSpeed * .72) * g_flTime).xyz);
        float3 wave = normalize(float3((a.xy + b.xy) * .28, 1));
        float3 world = i.vPositionWithOffsetWs + g_vCameraPositionWs;
        float3 bed = Depth::GetWorldPosition(i.vPositionSs.xy);
        float depth = max(0, world.z - bed.z);
        float shore = smoothstep(0, 9, depth);

        Material m = Material::From(i);
        m.Albedo = g_vWaterColor;
        m.Normal = TransformNormal(wave, i.vNormalWs, i.vTangentUWs, i.vTangentVWs);
        m.Roughness = .17;
        m.Metalness = .03;
        m.AmbientOcclusion = 1;
        m.Opacity = 1;
        float3 water = ShadingModelStandard::Shade(i, m).rgb;
        float3 view = normalize(g_vCameraPositionWs - world);
        float fresnel = pow(1 - saturate(abs(dot(view, m.Normal))), 4);
        float opacity = lerp(.30, .58, saturate(depth / 55));
        opacity = lerp(opacity, .90, fresnel);
        // A faint broken edge around shallow gravel, never an opaque white outline.
        float foam = (1 - smoothstep(4, 17, depth)) * shore * saturate((a.x + b.y) * 3 - .15) * .12;
        water = lerp(water, float3(.55,.61,.59), foam);
        return float4(water, shore * opacity);
    }
}
