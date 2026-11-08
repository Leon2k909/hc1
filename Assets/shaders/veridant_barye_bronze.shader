HEADER
{
    Description = "UV-mapped aged bronze retaining Rigsters sculpt normals";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth();
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
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From(i);
        float3 color = g_tColor.Sample(TextureFiltering, i.vTextureCoords.xy).rgb;
        float luma = dot(color, float3(.2126, .7152, .0722));
        float wear = smoothstep(.025, .20, luma);
        m.Albedo = lerp(float3(.060, .082, .068), float3(.135, .112, .078), wear)
            * lerp(.70, 1.15, smoothstep(.005, .24, luma));
        m.Roughness = .72;
        m.Metalness = .38;
        m.Opacity = 1;
        return ShadingModelStandard::Shade(i, m);
    }
}
