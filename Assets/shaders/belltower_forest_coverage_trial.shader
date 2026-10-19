HEADER
{
    Description = "Belltower forest mip-coverage comparison; original atlas and accepted lighting";
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
    CreateInputTexture2D( TexturePlants, Srgb, 8, "", "_color", "Plants", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tPlants < Channel( RGBA, Box( TexturePlants ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState PlantSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flCanopyMipCompensation < Default( 1 ); Range( 0, 1 ); UiGroup( "Canopy coverage,22/10" ); >;
    float g_flCanopyBrightness < Default( 1.0 ); Range( .05, 1.5 ); UiGroup( "Canopy,20/10" ); >;
    float g_flCanopyFadeStart < Default( 30000 ); Range( 1000, 60000 ); UiGroup( "Canopy,20/20" ); >;
    float g_flCanopyFadeEnd < Default( 52000 ); Range( 1001, 65000 ); UiGroup( "Canopy,20/30" ); >;
    // Reuse the landscape's original colour and normal inputs so its painted
    // canopy and these silhouettes have the same palette and slope lighting.
    CreateInputTexture2D( CanopyColorB, Srgb, 8, "", "_color", "Landscape B", Default3( .2, .3, .1 ) );
    CreateInputTexture2D( CanopyNormalB, Linear, 8, "", "_normal", "Landscape B", Default3( .5, .5, 1 ) );
    CreateInputTexture2D( CanopyColorC, Srgb, 8, "", "_color", "Landscape C", Default3( .2, .3, .1 ) );
    CreateInputTexture2D( CanopyNormalC, Linear, 8, "", "_normal", "Landscape C", Default3( .5, .5, 1 ) );
    CreateInputTexture2D( CanopyColorD, Srgb, 8, "", "_color", "Landscape D", Default3( .2, .3, .1 ) );
    CreateInputTexture2D( CanopyNormalD, Linear, 8, "", "_normal", "Landscape D", Default3( .5, .5, 1 ) );
    Texture2D g_tCanopyColorB < Channel( RGB, Box( CanopyColorB ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tCanopyNormalB < Channel( RGB, Box( CanopyNormalB ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    Texture2D g_tCanopyColorC < Channel( RGB, Box( CanopyColorC ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tCanopyNormalC < Channel( RGB, Box( CanopyNormalC ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    Texture2D g_tCanopyColorD < Channel( RGB, Box( CanopyColorD ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tCanopyNormalD < Channel( RGB, Box( CanopyNormalD ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState CanopySampler < Filter( ANISO ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    #undef MATERIAL_ALPHA_TEXTURE
    #define MATERIAL_ALPHA_TEXTURE g_tPlants
    #include "common/pixel.hlsl"
    StaticCombo( S_ALPHA_TEST, F_ALPHA_TEST, Sys( ALL ) );
    RenderState( CullMode, NONE );

    void CanopyZone( Texture2D colorMap, Texture2D normalMap, float margin, float weight,
        float2 plan, float2 dx, float2 dy, inout float3 color, inout float3 packed )
    {
        float2 corner = float2( -2380.0 - margin, 1800.0 + margin );
        float2 scale = float2( 1.0, -1.0 ) / ( float2( 4760.0, 3266.0 ) + 2.0 * margin );
        float2 uv = ( plan - corner ) * scale;
        // Average the ground over a crown footprint instead of copying an
        // individual bright grass texel or a painted leaf normal onto a card.
        // Landscape colours are 4096px and normal maps are 2048px.
        float crownLod = max( log2( 128.0 * 4096.0 * abs( scale.x ) ), 0.0 );
        color += weight * colorMap.SampleLevel( CanopySampler, uv, crownLod ).rgb;
        packed += weight * normalMap.SampleLevel( CanopySampler, uv, max( crownLod - 1.0, 0.0 ) ).rgb;
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float4 plant = g_tPlants.Sample( PlantSampler, i.vTextureCoords.xy );
        // At subpixel sizes, the painted canopy carries the distant hills.
        // Fade the cards before individual silhouettes become a noisy pattern.
        float distanceToCamera = length( m.WorldPosition - g_vCameraPositionWs );
        float fade = 1.0 - smoothstep( g_flCanopyFadeStart, max( g_flCanopyFadeStart + 1.0, g_flCanopyFadeEnd ), distanceToCamera );
        float canopyAlpha = plant.a * fade;
        // The engine subsequently multiplies alpha by (1 + .25 * mip).
        // Cancel only the requested share of that boost. Strength one takes
        // the untouched accepted path; mip zero is unchanged at every strength.
        [branch] if( g_flCanopyMipCompensation < 1.0 )
        {
            float2 texels = m.TextureCoords.xy * float2( TextureDimensions2DS( g_tPlants, 0 ) );
            float2 texelDx = ddx( texels );
            float2 texelDy = ddy( texels );
            float mip = max( 0.0, .5 * log2( max( max( dot( texelDx, texelDx ), dot( texelDy, texelDy ) ), .00000001 ) ) );
            float fullCorrection = 1.0 + .25 * mip;
            float requestedCorrection = 1.0 + .25 * mip * saturate( g_flCanopyMipCompensation );
            canopyAlpha *= requestedCorrection / fullCorrection;
        }
        m.Opacity = canopyAlpha;
        AdjustAlphaToCoverage( m );
        float2 plan = float2( -m.WorldPosition.y, m.WorldPosition.x );
        float2 dx = ddx( plan );
        float2 dy = ddy( plan );
        float reach = max( max( max( -2380.0 - plan.x, plan.x - 2380.0 ), 0.0 ),
            max( max( -1466.0 - plan.y, plan.y - 1800.0 ), 0.0 ) );
        float b = 1.0 - smoothstep( 6000.0 * .88, 6000.0, reach );
        float c = 1.0 - smoothstep( 34000.0 * .88, 34000.0, reach );
        float3 canopy = 0;
        float3 packed = 0;
        [branch] if( b > 0 ) CanopyZone( g_tCanopyColorB, g_tCanopyNormalB, 6000.0, b, plan, dx, dy, canopy, packed );
        [branch] if( (1-b)*c > 0 ) CanopyZone( g_tCanopyColorC, g_tCanopyNormalC, 34000.0, (1-b)*c, plan, dx, dy, canopy, packed );
        [branch] if( (1-b)*(1-c) > 0 ) CanopyZone( g_tCanopyColorD, g_tCanopyNormalD, 92000.0, (1-b)*(1-c), plan, dx, dy, canopy, packed );
        float leafDetail = clamp( dot( plant.rgb, float3( .2126, .7152, .0722 ) ) / .08, .25, 2.0 );
        m.Albedo = saturate( canopy * lerp( 1.0, leafDetail, .65 ) * g_flCanopyBrightness );
        m.Roughness = .9;
        m.Metalness = 0;
        float2 tilt = packed.rg * 2.0 - 1.0;
        m.Normal = normalize( float3( tilt.y, -tilt.x, sqrt( saturate( 1.0 - dot( tilt, tilt ) ) ) ) );
        m.GeometricNormal = m.Normal;
        // These are whole-canopy impostors. A single horizontal normal's
        // specular lobe makes every distant tree flash like a pale square.
        // Retain engine diffuse lighting and fog, without that planar reflection.
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
