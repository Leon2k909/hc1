// Ares' dust-covered sedimentary land. World-space sampling and a continuous slope blend keep the terrain grid
// out of the image. Bedrock is triplanar, with its layers aligned to world height on the escarpments.
HEADER
{
    Description = "Ares Martian dust and sedimentary bedrock";
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/pixel.hlsl"
    #if ( S_MODE_DEPTH == 0 )
        RenderState( DepthFunc, EQUAL );
        RenderState( DepthWriteEnable, false );
    #endif

    float g_flDustTile < Default( 640.0 ); UiGroup( "Land,10/10" ); >;
    float g_flRockTile < Default( 1024.0 ); UiGroup( "Land,10/20" ); >;
    CreateInputTexture2D( DustColor, Srgb, 8, "", "_color", "Dust,20/10", Default3( .5, .4, .3 ) );
    CreateInputTexture2D( DustNormal, Linear, 8, "", "_normal", "Dust,20/20", Default3( .5, .5, 1 ) );
    CreateInputTexture2D( RockColor, Srgb, 8, "", "_color", "Rock,30/10", Default3( .4, .3, .25 ) );
    CreateInputTexture2D( RockNormal, Linear, 8, "", "_normal", "Rock,30/20", Default3( .5, .5, 1 ) );
    Texture2D g_tDustColor < Channel( RGB, Box( DustColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tDustNormal < Channel( RGB, Box( DustNormal ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    Texture2D g_tRockColor < Channel( RGB, Box( RockColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tRockNormal < Channel( RGB, Box( RockNormal ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    TextureAttribute( LightSim_DiffuseAlbedoTexture, g_tDustColor );
    TextureAttribute( RepresentativeTexture, g_tDustColor );
    SamplerState GroundSampler < Filter( ANISO ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;

    #if ( S_MODE_DEPTH == 0 )
        [earlydepthstencil]
    #endif
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        float3 p = m.WorldPosition;
        float3 surface = normalize( i.vNormalWs.xyz );
        float2 dustUv = float2( -p.y, -p.x ) / g_flDustTile;
        float3 dust = g_tDustColor.Sample( GroundSampler, dustUv ).rgb;
        float3 macro = g_tDustColor.Sample( GroundSampler, dustUv * .173 + .37 ).rgb;
        dust = lerp( dust, macro, .22 );

        float3 weights = pow( abs( surface ), 4.0 );
        weights /= max( weights.x + weights.y + weights.z, .0001 );
        float2 uvX = p.yz / g_flRockTile;
        float2 uvY = p.xz / g_flRockTile;
        float2 uvZ = p.xy / g_flRockTile;
        float3 rock = g_tRockColor.Sample( GroundSampler, uvX ).rgb * weights.x
            + g_tRockColor.Sample( GroundSampler, uvY ).rgb * weights.y
            + g_tRockColor.Sample( GroundSampler, uvZ ).rgb * weights.z;
        // The feathered transition follows the interpolated slope, rather than selecting whole triangles.
        float exposed = smoothstep( .10, .43, 1.0 - saturate( surface.z ) );
        m.Albedo = saturate( lerp( dust, rock, exposed ) );

        float3 nDust = g_tDustNormal.Sample( GroundSampler, dustUv ).rgb * 2.0 - 1.0;
        float3 nX = g_tRockNormal.Sample( GroundSampler, uvX ).rgb * 2.0 - 1.0;
        float3 nY = g_tRockNormal.Sample( GroundSampler, uvY ).rgb * 2.0 - 1.0;
        float3 nZ = g_tRockNormal.Sample( GroundSampler, uvZ ).rgb * 2.0 - 1.0;
        float3 dustBump = float3( nDust.y, -nDust.x, 0 );
        float3 rockBump = float3( 0, nX.x, -nX.y ) * weights.x
            + float3( nY.x, 0, -nY.y ) * weights.y + float3( nZ.x, -nZ.y, 0 ) * weights.z;
        float3 bump = lerp( dustBump, rockBump, exposed );
        bump -= surface * dot( bump, surface );
        float strength = lerp( .7, .22, smoothstep( 1200.0, 9000.0, length( i.vPositionWithOffsetWs.xyz ) ) );
        m.Normal = normalize( surface + bump * strength );
        m.Roughness = lerp( .94, .9, exposed );
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        return ShadingModelStandard::Shade( i, m );
    }
}
