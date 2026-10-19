HEADER
{
    Description = "Belltower mean-matched canopy detail trial; original RGBA atlas";
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
    float4 g_vCanopyDetailKnee < Default4( 0.007050308399, 0.006554398686, 0.005510932766, 0.006699017249 ); UiGroup( "Canopy detail,21/10" ); >;
    float g_flCanopyDetailBlend < Default( 1 ); Range( 0, 1 ); UiGroup( "Canopy detail,21/20" ); >;
    float4 g_vCanopyChromaMean0 < Default4( 1.085583091, 1.022813678, 0.497096628, 1 ); UiGroup( "Canopy detail,21/30" ); >;
    float4 g_vCanopyChromaMean1 < Default4( 1.036157608, 1.046592593, 0.4245122373, 1 ); UiGroup( "Canopy detail,21/31" ); >;
    float4 g_vCanopyChromaMean2 < Default4( 1.05931294, 1.018914342, 0.6207541227, 1 ); UiGroup( "Canopy detail,21/32" ); >;
    float4 g_vCanopyChromaMean3 < Default4( 1.01030755, 1.035482287, 0.5521099567, 1 ); UiGroup( "Canopy detail,21/33" ); >;
    float g_flCanopyChromaDetail < Default( .8 ); Range( 0, 1 ); UiGroup( "Canopy detail,21/40" ); >;
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
        m.Opacity = plant.a * fade;
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
        float sourceLuma = dot( plant.rgb, float3( .2126, .7152, .0722 ) );
        float oldDetail = clamp( sourceLuma / .08, .25, 2.0 );
        // The UV windows remain within their original source-image cells.
        // Match each cell's mean, retaining variation inside the old limits.
        float rightCell = step( 0.555, i.vTextureCoords.x );
        float bottomCell = step( 0.539, i.vTextureCoords.y );
        float knee = lerp( lerp( g_vCanopyDetailKnee.x, g_vCanopyDetailKnee.y, rightCell ),
                           lerp( g_vCanopyDetailKnee.z, g_vCanopyDetailKnee.w, rightCell ), bottomCell );
        float signal = sourceLuma * sourceLuma;
        float smoothDetail = .25 + 1.75 * signal / ( signal + max( knee, 0.000001 ) );
        float3 sourceChroma = clamp( plant.rgb / max( sourceLuma, .005 ), .2, 3.0 );
        float3 meanChroma = lerp( lerp( g_vCanopyChromaMean0.xyz, g_vCanopyChromaMean1.xyz, rightCell ),
                                 lerp( g_vCanopyChromaMean2.xyz, g_vCanopyChromaMean3.xyz, rightCell ), bottomCell );
        float chromaConfidence = smoothstep( .65, .95, plant.a ) * saturate( g_flCanopyChromaDetail );
        float3 chroma = lerp( float3( 1, 1, 1 ), sourceChroma / max( meanChroma, .01 ), chromaConfidence );
        float oldResponse = lerp( 1.0, oldDetail, .65 );
        float3 smoothResponse = lerp( 1.0, smoothDetail, .65 ) * chroma;
        // Return toward the accepted tint as the existing distant cards fade.
        float3 canopyDetail = lerp( float3( oldResponse, oldResponse, oldResponse ), smoothResponse, saturate( g_flCanopyDetailBlend ) * fade );
        m.Albedo = saturate( canopy * canopyDetail * g_flCanopyBrightness );
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
