HEADER
{
    Description = "Cerro Blanco enamelled panels: each panel a little off flat, open joints, rain streaks under them";
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
    // The panels: g_flTilesPerUv panels to a UV unit (the model's UVs run one unit per 120 inches), each g_flSlabSize
    // inches square with open joints g_flJointWidth wide.
    float g_flTilesPerUv < Default( 4 ); UiGroup( "Panel" ); >;
    float g_flSlabSize < Default( 30 ); UiGroup( "Panel" ); >;
    float g_flTextureScale < Default( .25 ); UiGroup( "Panel" ); >;
    float g_flJointWidth < Default( .5 ); UiGroup( "Panel" ); >;
    float g_flBevelWidth < Default( .16 ); UiGroup( "Panel" ); >;
    // How far each panel is off flat: a random tilt (radians) and a pillowed face (its middle proud by this many inches).
    float g_flTilt < Default( .012 ); UiGroup( "Panel" ); >;
    float g_flPillow < Default( .05 ); UiGroup( "Panel" ); >;
    float g_flVariation < Default( .025 ); UiGroup( "Panel" ); >;
    float g_flStreaks < Default( .07 ); UiGroup( "Panel" ); >;
    float g_flPanelRoughness < Default( .34 ); UiGroup( "Panel" ); >;
    float g_flNormalStrength < Default( 1 ); UiGroup( "Panel" ); >;
    float3 g_vPanelTint < Default3( 1, 1, 1 ); UiGroup( "Panel" ); >;
    float3 g_vJointColor < Default3( .035, .034, .033 ); UiGroup( "Panel" ); >;

    float PanelHash( float2 p ) { return frac( sin( dot( p, float2( 127.1, 311.7 ) ) ) * 43758.5453 ); }
    float Noise1( float x )
    {
        float i = floor( x ), f = frac( x );
        float u = f * f * ( 3 - 2 * f );
        return lerp( PanelHash( float2( i, 7.13 ) ), PanelHash( float2( i + 1, 7.13 ) ), u );
    }
    float4 MainPs( PixelInput input ) : SV_Target0
    {
        Material material = Material::Init( input );
        #if !S_MODE_DEPTH
        float2 grid = input.vTextureCoords.xy * g_flTilesPerUv;
        float2 dx = ddx( grid ), dy = ddy( grid );
        float2 cell = floor( grid );
        float2 local = frac( grid );
        float h1 = PanelHash( cell + 5.3 ), h2 = PanelHash( cell + 19.7 ), h3 = PanelHash( cell + 43.1 );
        float h4 = PanelHash( cell + 91.7 ), h5 = PanelHash( cell + 63.9 );
        float3 toCamera = g_vCameraPositionWs - material.WorldPosition;
        float distance = length( toCamera );
        float near = 1 - smoothstep( 900, 2600, distance );

        // Each panel samples its own part of the enamel's mottle.
        float2 uv = grid * g_flTextureScale + float2( h1, h2 ) * 3.0;
        float2 sx = dx * g_flTextureScale, sy = dy * g_flTextureScale;
        float3 color = g_tColor.SampleGrad( TextureFiltering, uv, sx, sy ).rgb;
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, sx, sy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, sx, sy );

        // The joint: an open shadow gap, its arrises a hair rounded. It's box-filtered over the pixel's footprint across
        // it, so further off, where the gap is narrower than a pixel, it only darkens a pixel by the share it covers: a
        // fine grid, not a tiled wall's grout.
        float2 edgeInches = min( local, 1 - local ) * g_flSlabSize;
        float edge = min( edgeInches.x, edgeInches.y );
        float aa = max( length( float2( length( dx ), length( dy ) ) ) * g_flSlabSize * .35, .008 );
        float2 footprint = max( float2( length( float2( dx.x, dy.x ) ), length( float2( dx.y, dy.y ) ) ) * g_flSlabSize, .004 );
        float halfJoint = g_flJointWidth * .5;
        float2 cover = saturate( ( min( edgeInches + footprint * .5, halfJoint ) - max( edgeInches - footprint * .5, -halfJoint ) ) / footprint );
        float joint = 1 - ( 1 - cover.x ) * ( 1 - cover.y );
        float bevel = saturate( ( edge - g_flJointWidth * .5 ) / max( g_flBevelWidth, .001 ) );
        float slope = 6 * bevel * ( 1 - bevel ) * .08 / max( g_flBevelWidth, .001 );
        slope *= saturate( g_flBevelWidth / max( aa * 2, .001 ) );
        float2 gradient = edgeInches.x < edgeInches.y ? float2( local.x < .5 ? 1 : -1, 0 ) : float2( 0, local.y < .5 ? 1 : -1 );

        // Off flat: a random tilt and a pillowed face, which is what makes a panelled façade reflect the sky unevenly.
        float2 tilt = ( float2( h3, h4 ) - .5 ) * 2 * g_flTilt;
        float2 c = local * 2 - 1;
        float2 pillow = float2( -4 * c.x * ( 1 - c.y * c.y ), -4 * c.y * ( 1 - c.x * c.x ) ) * g_flPillow * ( .5 + h5 ) / g_flSlabSize;
        float3 tangentNormal = DecodeNormal( normal.xyz );
        tangentNormal.xy *= g_flNormalStrength * ( .35 + .65 * near );
        // pillow is the face's slope (the gradient of its height), so the normal leans against it: added, it dished
        // the panels instead, the bevel's arrises leaning the other way.
        tangentNormal.xy += tilt - pillow * .5;
        tangentNormal.xy -= gradient * slope;
        tangentNormal = normalize( tangentNormal );

        // Rain streaks: under some panels' top edges the water has left fine grey runs. Up the face is along +V where
        // the tangent says so.
        float vUp = dot( normalize( input.vTangentVWs ), float3( 0, 0, 1 ) );
        float below = vUp > .5 ? ( 1 - local.y ) : ( vUp < -.5 ? local.y : 2 );
        float across = local.x * g_flSlabSize;
        float runs = Noise1( across / 1.3 + h2 * 97 ) * .6 + Noise1( across / .45 + h1 * 41 ) * .4;
        runs = saturate( ( runs - .45 ) * 2.2 );
        float reach = lerp( .12, .55, h3 );
        float streak = runs * exp( -below / reach ) * step( .35, h4 ) * g_flStreaks * near;
        // And the panels' broad differences: no two quite the same white.
        float broad = .5 + .5 * sin( material.WorldPosition.x / 517 + sin( material.WorldPosition.y / 389 ) );
        color *= ( 1 + ( h5 - .5 ) * 2 * g_flVariation ) * lerp( .985, 1.012, broad ) * ( 1 - streak );
        float3 enamel = color * g_vPanelTint;
        float3 albedo = lerp( enamel, g_vJointColor, joint );
        material.Albedo = albedo * g_flTintColor * input.vVertexColor.rgb;
        material.Normal = TransformNormal( tangentNormal, input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
        material.Roughness = lerp( saturate( g_flPanelRoughness + ( rma.r - .5 ) * .2 + ( h1 - .5 ) * .06 + streak * 1.4 ), .92, joint );
        // The joint's occlusion by its share of the light the pixel reflects, not of its area: the albedo already darkens
        // a part-covered pixel by its share, and both lerped by the area darkened it twice in the shade (a half-covered
        // pixel ~35% too dark), so the grid read too strong from mid distance. Exact for the diffuse product.
        float3 luma = float3( .2126, .7152, .0722 );
        float occluded = joint * dot( g_vJointColor, luma ) / max( dot( albedo, luma ), .001 );
        material.AmbientOcclusion = lerp( rma.b, .25, occluded );
        material.TintMask = normal.a;
        material.TextureCoords = uv;
        #endif
        material.Metalness = 0;
        material.Transmission = 0;
        material.Opacity = 1;
        return ShadingModelStandard::Shade( input, material );
    }
}
