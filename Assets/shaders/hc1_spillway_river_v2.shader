HEADER
{
    Description = "Spillway tailrace: running alpine water, turbulent eddies and advected whitewater";
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
    float g_flBankFade < Default( .3 ); Range( .1, 4 ); UiGroup( "Water" ); >;
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

    float SWHash( float2 p ) { return frac( sin( dot(p,float2(127.1,311.7)) )*43758.5453 ); }
    float SWNoise( float2 p )
    {
        float2 a=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(SWHash(a),SWHash(a+float2(1,0)),f.x),lerp(SWHash(a+float2(0,1)),SWHash(a+1),f.x),f.y);
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
        float2 pixelDx = ddx( world.xy );
        float2 pixelDy = ddy( world.xy );
        float3 waves = 0;
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( 1, .22 ), g_flRippleTile * .93, .110, .3, -.24 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .82, -.57 ), g_flRippleTile * .67, .075, 1.8, -.32 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .44, .90 ), g_flRippleTile * .43, .055, 3.1, -.43 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .97, -.24 ), g_flRippleTile * .28, .040, 4.6, -.61 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .68, .73 ), g_flRippleTile * .17, .028, 2.3, -.83 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .92, .39 ), g_flRippleTile * .11, .018, 5.7, -1.13 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .53, -.85 ), g_flRippleTile * .073, .012, .9, -1.42 );
        waves += FilteredRipple( position, pixelDx, pixelDy, float2( .98, -.17 ), g_flRippleTile * .049, .008, 4.1, -1.77 );
        water.Normal = normalize( input.vNormalWs + float3( waves.xy * g_flRippleStrength, 0 ) );
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
        water.Opacity = 1 - ( 1 - fresnel ) * transmission;
        water.Albedo = g_vWaterColor * ( 1 - transmission );

        float2 swp = position / float2(88,37);
        float swWarp = SWNoise(swp*.43 + g_flTime*.06);
        float swNoise = SWNoise(swp + swWarp*3)*.65 + SWNoise(swp*2.4 + swWarp*5)*.35;
        float swFoam = smoothstep(.64,.79,swNoise) * .32;
        water.Albedo = lerp(water.Albedo,float3(.27,.30,.31),swFoam);
        water.Roughness = lerp(water.Roughness,.48,swFoam);
        water.Opacity = lerp(water.Opacity,1,swFoam);

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
        // The harbour and the small bank pools are at different elevations.
        // Retain their local cubemaps instead of projecting the canal mirror
        // onto a surface that does not lie in its reflection plane.
        if ( g_bWaterReflection && abs( world.z - g_flWaterReflectionPlane ) < .5 )
        {
            float2 uv = input.vPositionSs.xy * g_vInvViewportSize;
            // A world-X wave must not always shift the image horizontally.
            // Project the perturbed reflection direction through this camera,
            // mirrored back over the flat capture plane, before offsetting UVs.
            float3 reflectionDelta = reflect( -view, water.Normal )
                                   - reflect( -view, normalize( input.vNormalWs ) );
            reflectionDelta.z = -reflectionDelta.z;
            float2 viewDelta = mul( g_matWorldToView, float4( reflectionDelta, 0 ) ).xy;
            float aspect = g_vInvViewportSize.x / g_vInvViewportSize.y;
            uv += float2( viewDelta.x * aspect, -viewDelta.y ) * .014;
            if ( g_bWaterReflectionFlip ) uv.y = 1 - uv.y;
            reflection = g_tWaterReflection.SampleLevel( WaterReflectionSampler, saturate( uv ), 0 ).rgb
                * CalcBRDFReflectionFactor( ndotv, water.Roughness, lightingInput.vSpecularColor );
        }
        float3 lit = ( lighting.vDiffuse.rgb + ambient ) * lightingInput.vDiffuseColor.rgb
                     + lighting.vSpecular.rgb + reflection;
        float4 color = DoAtmospherics( world, input.vPositionSs.xy, float4( lit, water.Opacity ) );
        // The standard shader adds fog as a straight color. Scale that added term for premultiplied water.
        float3 fog = DoAtmospherics( world, input.vPositionSs.xy, float4( 0, 0, 0, 1 ) ).rgb;
        color.rgb = max( 0, color.rgb - fog * ( 1 - water.Opacity ) );
        return color * bank;
    }
}
