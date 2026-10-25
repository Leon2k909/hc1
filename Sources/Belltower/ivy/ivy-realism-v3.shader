HEADER
{
    Description = "Individual ivy blades: cupped normals, waxy tops and diffuse undersides";
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
        float4 plant = g_tPlants.Sample( PlantSampler, i.vTextureCoords.xy );
        i.vNormalWs *= i.face ? 1 : -1;
        Material m = Material::From( i );
        m.Albedo = plant.rgb * ( i.face ? float3(1,1,1) : float3(.88,1.02,.86) );
        m.Opacity = plant.a;
        m.Roughness = i.face ? .57 : .72;
        m.Metalness = 0;
        m.Transmission = float3(.13,.18,.085);
        m.Normal = normalize( i.vNormalWs );
        m.GeometricNormal = m.Normal;
        return ShadingModelStandard::Shade( i, m );
    }
}
