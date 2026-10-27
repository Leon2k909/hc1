HEADER
{
    Description = "Clear accelerating fountain jets with flowing highlights and aerated water";
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
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float3 p = m.WorldPosition;
        // Phase travels downward along the falling water, in world coordinates.
        float phase = p.z * 1.65 + g_flTime * 13;
        float crossPhase = p.x * 2.9 + p.y * 3.7;
        float bubbles = sin(phase * 1.7 + crossPhase) * sin(phase * .83 - crossPhase * 1.3);
        float foam = (.16 + .84 * pow(saturate(bubbles * .5 + .5), 3)) * (1 - smoothstep(54, 90, p.z));
        float3 folds = normalize(float3(sin(phase + crossPhase) * .13, cos(phase * .71) * .10, 1));
        m.Normal = TransformNormal(folds, i.vNormalWs, i.vTangentUWs, i.vTangentVWs);
        float fresnel = pow(1 - saturate(dot(normalize(-i.vPositionWithOffsetWs), m.Normal)), 3);
        m.Albedo = lerp(float3(.08, .17, .20), float3(.88, .94, .96), foam);
        m.Roughness = .065 + foam * .24;
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        m.Opacity = saturate(.32 + fresnel * .36 + foam * .38);
        return ShadingModelStandard::Shade(i, m);
    }
}
