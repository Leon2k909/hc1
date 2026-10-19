HEADER
{
    Description = "Lowtide tidal water: moving ripples, reflected light and shallow-bank transparency";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
}
COMMON
{
    #define S_SPECULAR 1
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
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"

    BoolAttribute( DoNotCastShadows, true );
    RenderState( DepthWriteEnable, false );
    RenderState( DepthEnable, true );
    // Premultiplied blending keeps the reflection visible even in very shallow water.
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, ONE );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( SrcBlendAlpha, ONE );
    RenderState( DstBlendAlpha, INV_SRC_ALPHA );
    RenderState( CullMode, NONE );

    float3 g_vWaterColor < UiType( Color ); Default3( .10, .16, .14 ); UiGroup( "Water" ); >;
    float2 g_vWaterFlow < Default2( -3.4, .9 ); UiGroup( "Water" ); >;
    float g_flRippleTile < Default( 48 ); Range( 16, 2048 ); UiGroup( "Water" ); >;
    float g_flRippleStrength < Default( .8 ); Range( 0, 2 ); UiGroup( "Water" ); >;
    float g_flWaterRoughness < Default( .10 ); Range( .04, .5 ); UiGroup( "Water" ); >;
    float g_flAbsorptionDistance < Default( 42 ); Range( 4, 256 ); UiGroup( "Water" ); >;
    float g_flBankFade < Default( 4 ); Range( .1, 12 ); UiGroup( "Water" ); >;
    SamplerState WaterSurfaceSampler < Filter( ANISO ); AddressU( WRAP ); AddressV( WRAP ); >;
    CreateInputTexture2D( OceanSwell, Linear, 8, "", "_normal", "Water", Default3( .5, .5, 1 ) );
    CreateInputTexture2D( OceanChop, Linear, 8, "", "_normal", "Water", Default3( .5, .5, 1 ) );
    Texture2D g_tOceanSwell < Channel( RGB, Box( OceanSwell ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    Texture2D g_tOceanChop < Channel( RGB, Box( OceanChop ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    Texture2D g_tWaterReflection < Attribute( "LowtideReflection" ); SrgbRead( false ); >;
    SamplerState WaterReflectionSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    bool g_bWaterReflection < Attribute( "LowtideReflectionEnabled" ); >;
    bool g_bWaterReflectionFlip < Attribute( "LowtideReflectionFlip" ); >;
    float g_flWaterReflectionPlane < Attribute( "LowtideReflectionPlane" ); >;

    float3 FilteredRipple( float2 position, float2 pixelDx, float2 pixelDy, float2 direction,
                          float wavelength, float slope, float phase, float speed )
    {
        direction = normalize( direction );
        float2 waveVector = direction * ( 6.28318530718 / wavelength );
        // Fade before the Nyquist limit. A grazing view can cover several crests in a single pixel.
        float footprint = max( abs( dot( waveVector, pixelDx ) ), abs( dot( waveVector, pixelDy ) ) );
        float resolved = 1 - smoothstep( .65, 2.4, footprint );
        float angle = dot( waveVector, position ) + phase + g_flTime * speed;
        float2 normalSlope = direction * ( slope * cos( angle ) * resolved );
        // Carry unresolved slope energy into roughness instead of sparkling or turning perfectly mirror-smooth.
        float variance = .5 * slope * slope * ( 1 - resolved * resolved );
        return float3( normalSlope, variance );
    }

    float g_flReflectionFilter < Default( 0.08 ); Range( 0, 2 ); UiGroup( "Water" ); >;

    float3 FilteredPlanarReflection( float2 uv, float roughness )
    {
        uint width, height, levels;
        g_tWaterReflection.GetDimensions( 0, width, height, levels );
        float2 size = max( float2( width, height ), 1 );
        float2 dx = ddx( uv ) * size;
        float2 dy = ddy( uv ) * size;
        float footprint = max( length( dx ), length( dy ) );
        // Perceptual roughness squared is the microfacet slope parameter.
        // Project an approximate reflected cone into the capture's pixel scale.
        // The mip pyramid is a bounded box-filter approximation, not a full
        // view-dependent GGX convolution or a correction for reflection depth.
        float2 projection = abs( float2( g_matViewToProjection[0][0], g_matViewToProjection[1][1] ) );
        float cone = roughness * roughness * max( size.x * projection.x, size.y * projection.y );
        float diameter = max( footprint, cone * g_flReflectionFilter );
        float lod = clamp( log2( max( diameter, 1 ) ), 0, max( float( levels ) - 1, 0 ) );
        // An old one-level target remains valid during a guarded staged import.
        return g_tWaterReflection.SampleLevel( WaterReflectionSampler, uv, lod ).rgb;
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        // Explicit water draws also run in child views. The reflected camera is
        // behind this plane, so it must never sample its own render target.
        if ( g_bWaterReflection && g_vCameraPositionWs.z < g_flWaterReflectionPlane ) discard;
        Material water = Material::Init( input );
        float3 world = water.WorldPosition;
        // Continuous wave gradients have no source texels, compression blocks or repeating noise tiles.
        // World anchoring keeps the channel, harbour and puddles in phase without moving their geometry.
        float2 position = world.xy - g_vWaterFlow * g_flTime;
        // Distort wave phases on two independent large scales so the sea does
        // not turn into a uniform array of horizontal sine-wave stripes.
        float2 warp = float2(
            sin( position.y * .0043 + sin( position.x * .0017 ) * 2.1 )
                + .55 * sin( position.x * .0027 - position.y * .0013 ),
            sin( position.x * .0031 - cos( position.y * .0023 ) * 1.7 )
                + .50 * cos( position.y * .0037 + position.x * .0011 ) );
        position += warp * ( g_flRippleTile * 1.25 );
        float2 pixelDx = ddx( position );
        float2 pixelDy = ddy( position );
        float3 waves = 0;
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( 1, .31 ), g_flRippleTile * 3.8, .045, .3, -.24 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .64, -.77 ), g_flRippleTile * 2.3, .037, 1.8, -.32 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .44, .90 ), g_flRippleTile * 1.4, .034, 3.1, -.43 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( -.87, .49 ), g_flRippleTile * .78, .028, 4.6, -.61 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .68, .73 ), g_flRippleTile * .17, .028, 2.3, -.83 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .92, .39 ), g_flRippleTile * .11, .018, 5.7, -1.13 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .53, -.85 ), g_flRippleTile * .073, .012, .9, -1.42 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .98, -.17 ), g_flRippleTile * .049, .008, 4.1, -1.77 );
        // Two spectral normal fields supply broken, irregular wave crests.
        // Different scales and velocities prevent recognisable repeats.
        float2 swellUv = ( world.xy - g_vWaterFlow * g_flTime ) / 1100.0;
        float2 chopUv = ( world.xy - float2( .63, -1.41 ) * g_flTime ) / 460.0;
        float3 swell = DecodeNormal( g_tOceanSwell.Sample( WaterSurfaceSampler, swellUv ).xyz );
        float3 chop = DecodeNormal( g_tOceanChop.Sample( WaterSurfaceSampler, chopUv ).xyz );
        // Water is gravitationally horizontal even where the channel model
        // descends into the harbour. Using that ramp's geometric normal made
        // its whole trapezoid reflect a different sky and gave it a hard edge.
        const float3 flatWaterNormal = float3( 0, 0, 1 );
        float2 surfaceSlope = swell.xy * .32 + chop.xy * .24 + waves.xy * g_flRippleStrength;
        water.Normal = normalize( flatWaterNormal + float3( surfaceSlope, 0 ) );
        water.Roughness = sqrt( g_flWaterRoughness * g_flWaterRoughness + waves.z * g_flRippleStrength * g_flRippleStrength );
        water.Metalness = 0;
        water.AmbientOcclusion = 1;

        // Only opaque geometry supplies depth. Water never writes its plane into the depth buffer.
        float3 bed = Depth::GetWorldPosition( input.vPositionSs.xy );
        float depth = max( 0, world.z - bed.z );
        float bank = smoothstep( 0, g_flBankFade, depth );
        float path = min( length( world - bed ), 8192 );
        float transmission = exp( -path / g_flAbsorptionDistance );
        float3 view = g_matViewToProjection[3].w != 0 ? -g_vCameraDirWs : normalize( g_vCameraPositionWs - world );
        float ndotv = saturate( abs( dot( view, water.Normal ) ) );
        // Air/water IOR 1.333 gives F0 ~0.02037; the default dielectric .04
        // overstates reflectance when looking down at the shallow channel.
        const float waterF0 = .02037;
        float fresnel = saturate( CalcBRDFReflectionFactor( ndotv, water.Roughness, waterF0 ).x );
        water.Opacity = ( 1 - ( 1 - fresnel ) * transmission ) * bank;
        water.Albedo = g_vWaterColor * ( 1 - transmission );

        CombinerInput lightingInput = ShadingModelStandard::MaterialToCombinerInput( water );
        lightingInput.vSpecularColor = float3( waterF0, waterF0, waterF0 );
        // Wave variance is already filtered per pixel. Replacing it with quad derivatives makes 2x2 roughness blocks.
        lightingInput.vRoughness = water.Roughness.xx;
        LightingTerms_t lighting = InitLightingTerms();
        ComputeDirectLighting( lighting, lightingInput );
        float3 ambient = AmbientLight::From( world, input.vPositionSs, water.Normal );
        // SSR was traced against the opaque bed's depth/normal, not the transparent water surface.
        // Use filtered sky/local cubemaps for water, with the standard direct lighting and shadows.
        float3 reflection = EnvMap::From( world, input.vPositionSs, water.Normal, water.Roughness.xx )
                            * CalcBRDFReflectionFactor( ndotv, water.Roughness, lightingInput.vSpecularColor );
        // The canal and harbour share one horizontal water plane. A previous
        // world-X cutoff switched their reflection sources across a straight
        // line in the harbour, producing an obvious diagonal seam in perspective.
        // Only the separate, higher bank pools should retain cubemap reflections.
        // Fade the planar capture at the very edge of the water where the bed
        // meets the surface; the shallow edge already fades to transparency.
        float reflectionBlend = g_bWaterReflection
            ? ( 1 - smoothstep( .2, 6, abs( world.z - g_flWaterReflectionPlane ) ) )
                * smoothstep( 0, 3, depth ) : 0;
        if ( reflectionBlend > 0 )
        {
            float2 uv = input.vPositionSs.xy * g_vInvViewportSize;
            // A world-X wave must not always shift the image horizontally.
            // Project the perturbed reflection direction through this camera,
            // mirrored back over the flat capture plane, before offsetting UVs.
            float3 reflectionDelta = reflect( -view, water.Normal )
                                   - reflect( -view, flatWaterNormal );
            reflectionDelta.z = -reflectionDelta.z;
            float2 viewDelta = mul( g_matWorldToView, float4( reflectionDelta, 0 ) ).xy;
            float aspect = g_vInvViewportSize.x / g_vInvViewportSize.y;
            uv += float2( viewDelta.x * aspect, -viewDelta.y ) * .014;
            if ( g_bWaterReflectionFlip ) uv.y = 1 - uv.y;
            float3 planar = FilteredPlanarReflection( saturate( uv ), water.Roughness )
                * CalcBRDFReflectionFactor( ndotv, water.Roughness, lightingInput.vSpecularColor );
            reflection = lerp( reflection, planar, reflectionBlend );
        }
        float3 lit = ( lighting.vDiffuse.rgb + ambient ) * lightingInput.vDiffuseColor.rgb
                     + lighting.vSpecular.rgb * .68 + reflection;
        float4 color = DoAtmospherics( world, input.vPositionSs.xy, float4( lit, water.Opacity ) );
        // The standard shader adds fog as a straight color. Scale that added term for premultiplied water.
        float3 fog = DoAtmospherics( world, input.vPositionSs.xy, float4( 0, 0, 0, 1 ) ).rgb;
        color.rgb = max( 0, color.rgb - fog * ( 1 - water.Opacity ) );
        // Blend the shoreline using the same alpha as its premultiplied light.
        // Fading the final colour separately produced visible hard dark contours.
        color.rgb *= bank;
        return color;
    }
}
