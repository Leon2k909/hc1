HEADER
{
    Description = "Clear fountain beads with a soft grazing highlight";
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
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
        Material m = Material::Init(i);
        m.Normal = normalize(i.vNormalWs);
        float facing = saturate(dot(normalize(-i.vPositionWithOffsetWs), m.Normal));
        float rim = (1 - facing) * (1 - facing);
        m.Albedo = lerp(float3(.26, .35, .33), float3(.68, .74, .71), rim);
        m.Roughness = .15;
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        m.Opacity = .32 + .48 * rim;
        return ShadingModelStandard::Shade(i, m);
    }
}
