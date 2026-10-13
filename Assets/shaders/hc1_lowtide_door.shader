HEADER
{
    Description = "Lowtide loading doors: generated painted vertical timber at its real board scale";
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
    float4 g_vDoorRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Door" ); >;
    float2 g_vDoorScale < Default2( 1, 1 ); UiGroup( "Door" ); >;

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        // Repeat between complete board grooves. All maps share this region;
        // the generated albedo stays at its original resolution in the atlas.
        input.vTextureCoords.xy = g_vDoorRegion.xy + frac( input.vTextureCoords.xy * g_vDoorScale ) * g_vDoorRegion.zw;
        Material material = Material::From( input );
        return ShadingModelStandard::Shade( input, material );
    }
}
