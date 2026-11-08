HEADER
{
    Description = "Weathered cast bronze with diffuse mineral patina";
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
    #include "common/pixel.hlsl"

    float Grain( float3 p )
    {
        return sin(dot(p, float3(1.21, .83, 1.14))) * .42
             + sin(dot(p, float3(-1.71, 1.93, .73))) * .32
             + sin(dot(p, float3(.54, -.92, 2.52))) * .26;
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init(i);
        float3 p = m.WorldPosition;
        float patch = Grain(p * .29) + Grain(p * .82) * .36 + Grain(p * 3.7) * .13;
        float oxide = smoothstep(-.22, .72, patch) * .7;
        float grit = Grain(p * 5.6);
        float worn = smoothstep(.0, .85, i.vNormalWs.z) * (1 - oxide);
        float3 bronze = lerp(float3(.075, .056, .041), float3(.16, .111, .068), worn);
        m.Albedo = lerp(bronze, float3(.047, .085, .071), oxide) * (1 + grit * .12);
        m.Roughness = lerp(.57, .88, oxide) + grit * .045;
        m.Metalness = lerp(.74, .06, oxide);
        m.AmbientOcclusion = 1;
        m.Opacity = 1;
        m.Normal = TransformNormal(normalize(float3(grit * .06, Grain(p * 7.3) * .06, 1)),
            i.vNormalWs, i.vTangentUWs, i.vTangentVWs);
        return ShadingModelStandard::Shade(i, m);
    }
}
