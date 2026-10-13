HEADER
{
    Description = "Lowtide brick: repeat the generated scan between mortar boundaries";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth( S_MODE_DEPTH );
    ToolsShadingComplexity( "tools_shading_complexity.shader" );
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
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float4 g_vBrickRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Brick" ); >;
    float2 g_vBrickScale < Default2( 1, 1 ); UiGroup( "Brick" ); >;

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        // The generated albedo remains unchanged. Repeat an interior region whose top/bottom meet in bed joints;
        // this avoids joining two cut brick faces or doubling the border mortar at the scan's outer edges.
        input.vTextureCoords.xy = g_vBrickRegion.xy + frac( input.vTextureCoords.xy * g_vBrickScale ) * g_vBrickRegion.zw;
        Material material = Material::From( input );
        return ShadingModelStandard::Shade( input, material );
    }
}
