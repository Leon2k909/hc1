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

    // Calibrated from unchanged source alpha, not an edited normal-map bitmap.
    static const float4 CrownAtlasRect[16] = {
        float4(0.017543860, 0.748006380, 0.269537480, 0.973684211),
        float4(0.280701754, 0.748006380, 0.493620415, 0.981658692),
        float4(0.498405104, 0.748803828, 0.759968102, 0.932216906),
        float4(0.765550239, 0.748803828, 0.989633174, 0.956937799),
        float4(0.013556619, 0.508771930, 0.278309410, 0.697767145),
        float4(0.291866029, 0.507177033, 0.490430622, 0.732057416),
        float4(0.499202552, 0.507177033, 0.774322169, 0.689792663),
        float4(0.776714514, 0.503987241, 0.986443381, 0.719298246),
        float4(0.024720893, 0.257575758, 0.240829346, 0.492025518),
        float4(0.257575758, 0.255980861, 0.527113238, 0.472886762),
        float4(0.540669856, 0.255980861, 0.709728868, 0.490430622),
        float4(0.724880383, 0.259968102, 0.988835726, 0.480063796),
        float4(0.019936204, 0.022328549, 0.232057416, 0.247208931),
        float4(0.251196172, 0.021531100, 0.511961722, 0.216905901),
        float4(0.519936204, 0.023923445, 0.726475279, 0.238437002),
        float4(0.741626794, 0.019138756, 0.992025518, 0.244816587)
    };
    static const float4 CrownShape[16] = {
        float4(0.498417722, 0.473498233, 0.524841772, 0.485848057),
        float4(0.498127341, 0.493174061, 0.522977528, 0.478395904),
        float4(0.498475610, 0.480434783, 0.525213415, 0.474521739),
        float4(0.498220641, 0.467432950, 0.523576512, 0.473505747),
        float4(0.498493976, 0.449367089, 0.525331325, 0.460506329),
        float4(0.497991968, 0.515957447, 0.522108434, 0.451524823),
        float4(0.498550725, 0.541484716, 0.525695652, 0.450895197),
        float4(0.498098859, 0.527777778, 0.522794677, 0.412148148),
        float4(0.498154982, 0.496598639, 0.523154982, 0.467670068),
        float4(0.498520710, 0.477941176, 0.525502959, 0.477959559),
        float4(0.497641509, 0.510204082, 0.519858491, 0.496785714),
        float4(0.498489426, 0.489130435, 0.525302115, 0.502047101),
        float4(0.498120301, 0.484042553, 0.522932331, 0.500851064),
        float4(0.498470948, 0.465306122, 0.525183486, 0.473857143),
        float4(0.498069498, 0.492565056, 0.522606178, 0.509144981),
        float4(0.498407643, 0.487632509, 0.524777070, 0.500971731)
    };
    float2 DecodeCrownShape( float2 uv )
    {
        [unroll] for ( int n = 0; n < 16; ++n )
        {
            float4 rect = CrownAtlasRect[n];
            float2 cornerDistance = min( abs( uv - rect.xy ), abs( uv - rect.zw ) );
            if ( all( cornerDistance < .00035 ) )
            {
                float2 local = saturate( ( uv - rect.xy ) / ( rect.zw - rect.xy ) );
                return ( local - CrownShape[n].xy ) / CrownShape[n].zw;
            }
        }
        return float2( 0, -10 ); // Unknown UVs retain the original terrain normal.
    }

}
struct VertexInput
{
    #include "common/vertexinput.hlsl"
};
struct PixelInput
{
    #include "common/pixelinput.hlsl"
    float2 vCrownShape : TEXCOORD8;
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i )
    {
        PixelInput result = FinalizeVertex( ProcessVertex( i ) );
        result.vCrownShape = DecodeCrownShape( result.vTextureCoords.xy );
        return result;
    }
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

    
    float g_flCrownVolumeStrength < Default( 0 ); Range( 0, .8 ); UiGroup( "Crown volume,30/10" ); >;
    float3 CrownLightingNormal( PixelInput i, float3 worldPosition, float3 original )
    {
        float crownWindow = smoothstep( -1.55, -.85, i.vCrownShape.y );
        float strength = g_flCrownVolumeStrength * crownWindow;
        // Uniform branch only: quad derivatives must precede the varying crown mask.
        [branch] if ( g_flCrownVolumeStrength <= .00001 ) return original;
        float3 px = ddx( worldPosition ), py = ddy( worldPosition );
        float2 ux = ddx( i.vCrownShape ), uy = ddy( i.vCrownShape );
        float determinant = ux.x * uy.y - ux.y * uy.x;
        [branch] if ( abs( determinant ) <= 1e-12 ) return original;
        float3 across = normalize( ( px * uy.y - py * ux.y ) / determinant );
        float3 up = normalize( ( py * ux.x - px * uy.x ) / determinant );
        float3 face = normalize( cross( across, up ) );
        if ( dot( face, g_vCameraPositionWs - worldPosition ) < 0 ) face = -face;
        float2 q = i.vCrownShape;
        float bulge = sqrt( saturate( 1.0 - dot( q, q ) ) );
        float3 rounded = normalize( across * q.x + up * q.y + face * bulge );
        return normalize( lerp( original, rounded, strength ) );
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
        m.Normal = CrownLightingNormal( i, m.WorldPosition, m.Normal );
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
