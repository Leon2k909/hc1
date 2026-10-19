HEADER
{
    Description = "Lowtide solid timber and aged cast iron";
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    // Opaque RGB mips preserve the unmodified non-power-of-two generated scan.
    #define AlphaWeighted( color, opacity ) Box( color )
    #include "common/utils/Material.CommonInputs.hlsl"
    #undef AlphaWeighted
    #include "common/pixel.hlsl"
    float3 g_vStructureTint < Default3( 1, 1, 1 ); UiType( Color ); >;
    float2 g_vStructureUvScale < Default2( 1, 1 ); >;
    float g_flStructureRoughnessScale < Default( 1 ); Range( 0, 2 ); >;
    float g_flStructureRoughnessFloor < Default( .55 ); Range( 0, 1 ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        i.vTextureCoords.xy *= g_vStructureUvScale;
        Material m = Material::From( i );
        m.Albedo *= g_vStructureTint;
        m.Roughness = saturate( max( m.Roughness * g_flStructureRoughnessScale, g_flStructureRoughnessFloor ) );
        m.Metalness = 0;
        m.Transmission = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
