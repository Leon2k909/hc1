HEADER
{
    Description = "Reference-derived limestone and bronze fountain crown";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth( S_MODE_DEPTH );
}
COMMON
{
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    CreateInputTexture2D( TextureCrown, Srgb, 8, "", "_color", "Crown", Default3( .5, .5, .5 ) );
    Texture2D g_tCrown < Channel( RGB, Box( TextureCrown ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState CrownSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flStone < Default( 0 ); Range( 0, 1 ); UiGroup( "Crown" ); >;
    #include "common/pixel.hlsl"
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init(i);
        float2 uv = i.vTextureCoords.xy;
        float3 color = g_tCrown.Sample(CrownSampler, uv).rgb;
        float3 broad = g_tCrown.SampleLevel(CrownSampler, uv, 5).rgb;
        float luminance = dot(color, float3(.2126, .7152, .0722));
        float broadLuminance = dot(broad, float3(.2126, .7152, .0722));
        // Reduce studio shading while retaining the source's fine carving and oxide detail.
        float stone = g_flStone;
        float fine = clamp(luminance / max(.025, broadLuminance), .38, 1.85);
        float oxide = smoothstep(.82, 1.08, color.g / max(.02, color.r));
        float3 bronze = lerp(float3(.076, .071, .060), float3(.047, .079, .066), oxide);
        float3 limestone = float3(.27, .245, .205);
        m.Albedo = lerp(bronze, limestone, stone) * lerp(1, fine, .72);
        m.Metalness = lerp(.42, .0, stone);
        m.Roughness = lerp(.66, .84, stone);
        m.Normal = normalize(i.vNormalWs);
        m.AmbientOcclusion = lerp(.78, 1, smoothstep(.02, .14, luminance));
        m.Opacity = 1;
        return ShadingModelStandard::Shade(i, m);
    }
}
