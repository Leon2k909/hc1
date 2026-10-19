HEADER
{
    Description = "Belltower sparse ground pockets: original RGBA albedo";
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
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    CreateInputTexture2D( TextureDetail, Srgb, 8, "", "_color", "Ground detail", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tDetail < Channel( RGBA, Box( TextureDetail ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState DetailSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    #undef MATERIAL_ALPHA_TEXTURE
    #define MATERIAL_ALPHA_TEXTURE g_tDetail
    #include "common/pixel.hlsl"
    StaticCombo( S_ALPHA_TEST, F_ALPHA_TEST, Sys( ALL ) );
    float g_flDetailFadeStart < Default( 900 ); Range( 100, 3000 ); UiGroup( "Ground detail,20/10" ); >;
    float g_flDetailFadeEnd < Default( 1600 ); Range( 101, 4000 ); UiGroup( "Ground detail,20/20" ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float4 detail = g_tDetail.Sample( DetailSampler, i.vTextureCoords.xy );
        float distanceToCamera = length( m.WorldPosition - g_vCameraPositionWs );
        float fade = 1.0 - smoothstep( g_flDetailFadeStart, max( g_flDetailFadeStart + 1.0, g_flDetailFadeEnd ), distanceToCamera );
        m.Opacity = detail.a * fade;
        AdjustAlphaToCoverage( m );
        m.Albedo = detail.rgb;
        m.Roughness = .96;
        m.Metalness = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
