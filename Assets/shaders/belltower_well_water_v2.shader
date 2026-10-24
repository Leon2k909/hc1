HEADER
{
    Description = "Quiet garden well water: clear dark water and fine surface ripples";
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
    float3 g_vWaterColor < UiType(Color); Default3(.003,.008,.006); UiGroup("Water"); >;
    float g_flFlowSpeed < Default(.006); Range(0,.1); UiGroup("Water"); >;
    float g_flWaterOpacity < Default(.78); Range(0,1); UiGroup("Water"); >;
    float g_flRippleStrength < Default(.24); Range(0,.5); UiGroup("Water"); >;
    float g_flWaterRoughness < Default(.035); Range(.01,.3); UiGroup("Water"); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float2 uv = i.vTextureCoords.xy;
        float3 a = DecodeNormal(g_tNormalA.Sample(g_sFlow, uv * 1.6 + float2(.31, -.47) * g_flFlowSpeed * g_flTime).xyz);
        float3 b = DecodeNormal(g_tNormalB.Sample(g_sFlow, uv * 2.73 + float2(-.43, -.23) * g_flFlowSpeed * g_flTime).xyz);
        float3 wave = normalize(float3((a.xy + b.xy) * g_flRippleStrength, 1));
        Material m = Material::From(i);
        m.Albedo = g_vWaterColor;
        m.Normal = TransformNormal(wave, i.vNormalWs, i.vTangentUWs, i.vTangentVWs);
        m.Roughness = g_flWaterRoughness;
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        m.Opacity = 1;
        float3 colour = ShadingModelStandard::Shade(i, m).rgb;
        float3 view = normalize(-i.vPositionWithOffsetWs);
        // Clearer looking down into the shaft; reflective at grazing angles.
        float fresnel = pow(1 - saturate(abs(dot(view, m.Normal))), 5);
        return float4(colour, lerp(g_flWaterOpacity, .98, fresnel));
    }
}
