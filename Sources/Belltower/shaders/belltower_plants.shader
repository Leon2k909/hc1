HEADER
{
    Description = "Belltower plant cards using the generated atlas's original RGBA";
}
FEATURES
{
    #include "common/features.hlsl"
    Feature( F_ALPHA_TEST, 0..1, "Rendering" );
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
    #if PROGRAM == VFX_PROGRAM_PS
        bool face : SV_IsFrontFace;
    #endif
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    CreateInputTexture2D( TexturePlants, Srgb, 8, "", "_color", "Plants", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tPlants < Channel( RGBA, Box( TexturePlants ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState PlantSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    #undef MATERIAL_ALPHA_TEXTURE
    #define MATERIAL_ALPHA_TEXTURE g_tPlants
    #include "common/pixel.hlsl"
    StaticCombo( S_ALPHA_TEST, F_ALPHA_TEST, Sys( ALL ) );
    RenderState( CullMode, NONE );

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        i.vNormalWs *= i.face ? 1 : -1;
        Material m = Material::From( i );
        float4 plant = g_tPlants.Sample( PlantSampler, i.vTextureCoords.xy );
        m.Albedo = plant.rgb;
        m.Opacity = plant.a;
        m.Roughness = .8;
        m.Metalness = 0;
        m.Normal = normalize( i.vNormalWs );
        m.GeometricNormal = m.Normal;
        return ShadingModelStandard::Shade( i, m );
    }
}
