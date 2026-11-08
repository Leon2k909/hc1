HEADER
{
    Description = "Expanding fountain impact ripples";
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
        float2 p = i.vTextureCoords.xy * 2 - 1;
        float r = length(p);
        float drift = sin(p.x * 12 + p.y * 8 + g_flTime * 2) * .022;
        float wave = sin((r + drift) * 27 - g_flTime * 12);
        float crest = smoothstep(.72, .99, wave);
        float envelope = smoothstep(.09, .23, r) * (1 - smoothstep(.36, 1, r));
        float broken = .55 + .45 * sin(p.x * 15 - p.y * 12 + g_flTime * 1.7);
        return float4(.46, .59, .55, crest * envelope * broken * .13);
    }
}
