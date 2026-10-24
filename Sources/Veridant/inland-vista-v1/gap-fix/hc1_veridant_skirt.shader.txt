HEADER
{
    Description = "Veridant photographic distance impostors with native RGBA coverage and scene fog";
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
    #define S_TRANSLUCENT 1
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
    CreateInputTexture2D( TextureVista, Srgb, 8, "", "_color", "Vista", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tVista < Channel( RGBA, Box( TextureVista ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState VistaSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flVistaBrightness < Default( 1.0 ); Range( .05, 2.0 ); UiGroup( "Vista,10/10" ); >;
    #undef MATERIAL_ALPHA_TEXTURE
    #define MATERIAL_ALPHA_TEXTURE g_tVista
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"
    StaticCombo( S_ALPHA_TEST, F_ALPHA_TEST, Sys( ALL ) );
    RenderState( CullMode, NONE );
    RenderState( DepthWriteEnable, false );
    RenderState( DepthEnable, true );
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float4 vista = g_tVista.Sample( VistaSampler, i.vTextureCoords.xy );
        float radius = length( m.WorldPosition.xy - float2( -100.0, -75.0 ) );
        float blend = smoothstep( 4200.0, 6500.0, radius );
        m.Opacity = vista.a * blend;
        m.Albedo = vista.rgb * g_flVistaBrightness;
        m.Roughness = 1.0;
        m.Metalness = 0;
        // The photograph already carries local surface shading. A common
        // upward diffuse normal lets weather/exposure affect the whole vista
        // without revealing every flat strip as a differently lit panel.
        m.Normal = float3( 0, 0, 1 );
        m.GeometricNormal = m.Normal;
        CombinerInput combiner = ShadingModelStandard::MaterialToCombinerInput( m );
        LightingTerms_t lighting = InitLightingTerms();
        ComputeDirectLighting( lighting, combiner );
        CalculateIndirectLighting( lighting, combiner );
        float3 color = ( lighting.vDiffuse.rgb + lighting.vIndirectDiffuse.rgb ) * combiner.vDiffuseColor.rgb;
        if( DepthNormals::WantsDepthNormals() )
            return DepthNormals::Output( m.Normal, m.Roughness, m.Opacity );
        return DoAtmospherics( m.WorldPosition, m.ScreenPosition.xy, float4( color, m.Opacity ) );
    }
}
