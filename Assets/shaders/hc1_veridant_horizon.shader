HEADER
{
    Description = "Veridant fixed distant horizon with opaque joined ridges";
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
    CreateInputTexture2D( TextureVista, Srgb, 8, "", "_color", "Vista", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tVista < Channel( RGBA, Box( TextureVista ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState VistaSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flVistaBrightness < Default(1.0); >;
    float g_flImageU0 < Default(0.0); >;
    float g_flImageU1 < Default(1.0); >;
    float g_flCoastSide < Default(0.0); >;
    #undef MATERIAL_ALPHA_TEXTURE
    #define MATERIAL_ALPHA_TEXTURE g_tVista
    #include "common/pixel.hlsl"
    StaticCombo( S_ALPHA_TEST, F_ALPHA_TEST, Sys( ALL ) );
    RenderState( CullMode, NONE );

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init(i);
        float4 vista = g_tVista.Sample(VistaSampler,i.vTextureCoords.xy);
        float u = saturate((i.vTextureCoords.x-g_flImageU0)/(g_flImageU1-g_flImageU0));
        float coast = g_flCoastSide < -.5 ? u : 1-u;
        // The two outer ends descend to the water without stretching the image.
        float limit = lerp(-500.0,3500.0,smoothstep(0.0,.12,coast));
        float coastalCoverage = abs(g_flCoastSide)>.5 ? 1-smoothstep(limit-8,limit+8,m.WorldPosition.z) : 1;
        m.Opacity = vista.a*coastalCoverage;
        AdjustAlphaToCoverage(m);
        m.Albedo = vista.rgb*g_flVistaBrightness;
        m.Normal = float3(0,0,1);
        m.GeometricNormal = m.Normal;
        m.Roughness = 1;
        m.Metalness = 0;
        CombinerInput combiner = ShadingModelStandard::MaterialToCombinerInput(m);
        LightingTerms_t lighting = InitLightingTerms();
        ComputeDirectLighting(lighting,combiner);
        CalculateIndirectLighting(lighting,combiner);
        float3 color = (lighting.vDiffuse.rgb+lighting.vIndirectDiffuse.rgb)*combiner.vDiffuseColor.rgb;
        if (DepthNormals::WantsDepthNormals()) return DepthNormals::Output(m.Normal,m.Roughness,m.Opacity);
        return DoAtmospherics(m.WorldPosition,m.ScreenPosition.xy,float4(color,m.Opacity));
    }
}
