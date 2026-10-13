HEADER
{
    Description = "Lowtide warehouse lime plaster: fine mineral grain and floor-contact damp wear";
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
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float4 g_vPlasterRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Plaster" ); >;
    float g_flDampHeight < Default( 28 ); Range( 0, 72 ); UiGroup( "Plaster" ); >;
    float g_flDampStrength < Default( .4 ); Range( 0, 1 ); UiGroup( "Plaster" ); >;
    float3 g_vDampColor < Default3( .53, .49, .43 ); UiGroup( "Plaster" ); >;

    float PlasterHash( float2 point )
    {
        return frac( sin( dot( point, float2( 127.1, 311.7 ) ) ) * 43758.5453 );
    }

    float PlasterNoise( float2 point )
    {
        float2 cell = floor( point );
        float2 blend = frac( point );
        blend = blend * blend * ( 3 - 2 * blend );
        return lerp( lerp( PlasterHash( cell ), PlasterHash( cell + float2( 1, 0 ) ), blend.x ),
                     lerp( PlasterHash( cell + float2( 0, 1 ) ), PlasterHash( cell + 1 ), blend.x ), blend.y );
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        float2 repeat = input.vTextureCoords.xy;
        // Mirror alternating copies so opposite scan edges never form a
        // visible cut through the plaster. The grain and trowel relief need
        // the same orientation change as the sampled albedo.
        float2 mirrored = frac( floor( repeat ) * .5 ) * 2;
        float2 orientation = 1 - mirrored * 2;
        float2 phase = lerp( frac( repeat ), 1 - frac( repeat ), mirrored );
        float2 uv = g_vPlasterRegion.xy + phase * g_vPlasterRegion.zw;
        // Filter using the continuous mesh UVs, so atlas wraps do not create
        // false mip levels or blurry lines across the large warehouse walls.
        float2 dx = ddx( repeat ) * orientation * g_vPlasterRegion.zw;
        float2 dy = ddy( repeat ) * orientation * g_vPlasterRegion.zw;
        float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );
        Material material = Material::Init( input );
        material.Albedo = color.rgb * g_flTintColor * input.vVertexColor.rgb;
        float3 tangentNormal = DecodeNormal( normal.xyz );
        tangentNormal.xy *= orientation * smoothstep( 0, .0015, min( phase, 1 - phase ) );
        material.Normal = TransformNormal( normalize( tangentNormal ), input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
        material.Roughness = rma.r;
        material.AmbientOcclusion = rma.b;
        material.Metalness = 0;
        material.Transmission = 0;
        material.Opacity = 1;
        float3 world = material.WorldPosition;
        float along = world.x + world.y;
        // Broad variation has no mesh/tile boundary, so small scuffs and grain
        // can repeat without the whole warehouse displaying identical patches.
        material.Albedo *= lerp( .97, 1.015, PlasterNoise( float2( along, world.z ) * .017 ) );
        // Damp wear follows the ground-floor wall contact, rather than
        // repeating as horizontal bands beside every upper-storey window.
        float edge = max( 4, g_flDampHeight + ( PlasterNoise( float2( along / 52, 3.7 ) ) - .5 ) * 18 );
        float contact = 1 - smoothstep( 2, edge, world.z );
        float patches = lerp( .28, 1, PlasterNoise( float2( along * .04, world.z * .05 ) + 11.3 ) );
        float damp = contact * patches * g_flDampStrength;
        material.Albedo *= lerp( float3( 1, 1, 1 ), g_vDampColor, damp );
        material.Roughness = max( material.Roughness, .93 + contact * .035 );
        return ShadingModelStandard::Shade( input, material );
    }
}
