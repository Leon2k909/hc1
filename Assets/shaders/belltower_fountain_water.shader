HEADER
{
    Description = "Belltower fountain ripples and flowing spouts";
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
    float3 g_vWaterColor < UiType(Color); Default3(.07,.23,.25); UiGroup("Water"); >;
    float g_flFlowSpeed < Default(.18); Range(0,1); UiGroup("Water"); >;
    float g_flWaterOpacity < Default(.65); Range(0,1); UiGroup("Water"); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float2 uv = i.vTextureCoords.xy;
        float3 a = DecodeNormal(g_tNormalA.Sample(g_sFlow, uv + float2(.014, -g_flFlowSpeed) * g_flTime).xyz);
        float3 b = DecodeNormal(g_tNormalB.Sample(g_sFlow, uv * 1.71 + float2(-.021, -g_flFlowSpeed * .72) * g_flTime).xyz);
        float3 wave = normalize(float3((a.xy + b.xy) * .24, 1));
        Material m = Material::From(i);
        m.Albedo = g_vWaterColor;
        m.Normal = TransformNormal(wave, i.vNormalWs, i.vTangentUWs, i.vTangentVWs);
        m.Roughness = .12;
        m.Metalness = .02;
        m.AmbientOcclusion = 1;
        m.Opacity = 1;
        float3 colour = ShadingModelStandard::Shade(i, m).rgb;
        float3 world = i.vPositionWithOffsetWs + g_vCameraPositionWs;
        float3 view = normalize(g_vCameraPositionWs - world);
        float fresnel = pow(1 - saturate(abs(dot(view, m.Normal))), 4);
        return float4(colour, lerp(g_flWaterOpacity, .94, fresnel));
    }
}
