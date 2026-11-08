HEADER
{
    Description = "Clear fountain sheets with advected breakup and aeration";
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
        float2 uv = i.vTextureCoords.xy;
        float u = uv.x * 6.283185;
        float t = uv.y;
        float phase = (sqrt(t + .11) - .33166) * 53 - g_flTime * 31;
        float fold = sin(u * 3 + phase * .61 + sin(phase * .19)) * .56
                   + sin(u * 5 - phase * .83) * .29
                   + sin(u * 2 + phase * 1.37) * .15;
        float aeration = smoothstep(.06, .77, fold) * lerp(.23, .76, t);
        float continuity = lerp(1, lerp(.27, 1, smoothstep(-.66, .14, fold)), smoothstep(.33, .93, t));
        m.Normal = TransformNormal(normalize(float3(fold * .31, sin(phase + u * 2) * .16, 1)),
            i.vNormalWs, i.vTangentUWs, i.vTangentVWs);
        float fresnel = pow(1 - saturate(abs(dot(normalize(-i.vPositionWithOffsetWs), m.Normal))), 3);
        m.Albedo = lerp(float3(.18, .28, .29), float3(.83, .90, .89), aeration);
        m.Roughness = lerp(.095, .27, aeration);
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        m.Opacity = (.30 + .32 * fresnel + .46 * aeration) * continuity;
        return ShadingModelStandard::Shade(i, m);
    }
}
