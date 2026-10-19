HEADER
{
    Description = "Lowtide painted steel: enamel response, seam runoff and lower-rail weathering";
}
FEATURES
{
    #include "common/features.hlsl"
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
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float2 g_vContainerHeight < Default2( 0, 102 ); UiGroup( "Container" ); >;
    float g_flCoatRoughness < Default( .74 ); Range( .3, 1.5 ); UiGroup( "Container" ); >;
    float g_flWeathering < Default( .85 ); Range( 0, 1 ); UiGroup( "Container" ); >;
    float g_flIsRail < Default( 0 ); Range( 0, 1 ); UiGroup( "Container" ); >;

    float ContainerNoise( float2 p )
    {
        float2 cell = floor( p ), f = frac( p );
        f = f * f * ( 3 - 2 * f );
        float4 h = float4( dot( cell, float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 0 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 0, 1 ), float2( 127.1, 311.7 ) ),
            dot( cell + 1, float2( 127.1, 311.7 ) ) );
        h = frac( sin( h ) * 43758.5453 );
        return lerp( lerp( h.x, h.y, f.x ), lerp( h.z, h.w, f.x ), f.y );
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        Material material = Material::From( input );
        #if !S_MODE_DEPTH
        float3 world = material.WorldPosition;
        float h = world.z - g_vContainerHeight.x;
        float height = max( g_vContainerHeight.y, 1 );
        float vertical = 1 - smoothstep( .45, .9, abs( input.vNormalWs.z ) );
        float along = abs( input.vNormalWs.x ) > abs( input.vNormalWs.y ) ? world.y : world.x;
        float2 wall = float2( along, h );
        float broad = ContainerNoise( wall / float2( 128, 72 ) + 19.7 );
        float runoff = ContainerNoise( wall / float2( 3.2, 58 ) + 3.27 );
        float footprint = max( length( ddx( world ) ), length( ddy( world ) ) );
        float resolved = 1 - smoothstep( 1.5, 5, footprint );
        float fine = lerp( .5, ContainerNoise( wall / float2( 1.4, 3.6 ) + 47.1 ), resolved );
        float bottom = ( 1 - smoothstep( 2, 20 + broad * 14, h ) ) * ( .35 + runoff * .65 );
        float topSeam = exp2( -abs( h - ( height - 6 ) ) / 2.4 ) * ( .3 + runoff * .7 );
        float upperRun = 1 - smoothstep( 0, 28, height - h );
        float deposits = smoothstep( .58, .80, fine * .35 + runoff * .65 );
        float oxide = deposits * max( bottom * .66, upperRun * .55 ) * vertical * g_flWeathering;
        float dirt = saturate( bottom * .38 + topSeam * .22 ) * vertical * g_flWeathering;
        // Intact enamel stays dielectric. The existing scan's metallic chips
        // remain conductive unless covered by oxide; rust is rough dielectric.
        material.Albedo *= lerp( .87, 1.04, broad ) * ( 1 - dirt );
        material.Albedo = lerp( material.Albedo, float3( .095, .042, .013 ), oxide * .65 );
        material.Roughness = saturate( material.Roughness * g_flCoatRoughness * lerp( 1, .94, g_flIsRail ) );
        material.Roughness = lerp( material.Roughness, .88, saturate( max( dirt * .5, oxide * .9 ) ) );
        material.Metalness *= 1 - saturate( oxide );
        material.AmbientOcclusion *= 1 - topSeam * .23 * vertical * g_flWeathering;
        #endif
        material.Transmission = 0;
        material.Opacity = 1;
        return ShadingModelStandard::Shade( input, material );
    }
}
