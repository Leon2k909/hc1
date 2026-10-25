// Ares' enclosed processing column. All motion stays in this opaque emissive surface;
// no moving geometry, scene lights, particles or per-frame C# are needed.
HEADER
{
    Description = "Ares slowly circulating amber plasma";
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
    float3 vPositionOs : TEXCOORD8;
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i )
    {
        PixelInput o = ProcessVertex( i );
        o.vPositionOs = i.vPositionOs.xyz;
        return FinalizeVertex( o );
    }
}
PS
{
    #include "common/pixel.hlsl"
    #if ( S_MODE_DEPTH == 0 )
        RenderState( DepthFunc, EQUAL );
        RenderState( DepthWriteEnable, false );
    #endif

    CreateInputTexture2D( TextureColor, Srgb, 8, "", "_color", "Plasma,10/10", Default3( .8, .2, .02 ) );
    Texture2D g_tColor < Channel( RGB, Box( TextureColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    TextureAttribute( RepresentativeTexture, g_tColor );
    SamplerState PlasmaSampler < Filter( ANISO ); MaxAniso( 4 ); AddressU( WRAP ); AddressV( WRAP ); >;

    float g_flBrightness < Default( 1.8 ); Range( .1, 4 ); UiGroup( "Plasma,10/20" ); >;
    float g_flRiseSpeed < Default( .018 ); Range( 0, .1 ); UiGroup( "Flow,20/10" ); >;
    float g_flSwirlSpeed < Default( .008 ); Range( 0, .05 ); UiGroup( "Flow,20/20" ); >;
    float g_flFlowHeight < Default( 180 ); Range( 32, 512 ); UiGroup( "Flow,20/30" ); >;
    float g_flWarp < Default( .055 ); Range( 0, .15 ); UiGroup( "Flow,20/40" ); >;
    float g_flDarkAreas < Default( .85 ); Range( 0, 1 ); UiGroup( "Plasma,10/30" ); >;
    float g_flPulseAmount < Default( .03 ); Range( 0, .1 ); UiGroup( "Plasma,10/40" ); >;

    float PlasmaHash( float2 p, float period )
    {
        // The mesh wraps from U=0 to U=2. Wrap the noise lattice too, so there is no cylindrical seam.
        p.x -= floor( p.x / period ) * period;
        float3 q = frac( float3( p.xyx ) * .1031 );
        q += dot( q, q.yzx + 33.33 );
        return frac( ( q.x + q.y ) * q.z );
    }

    float PlasmaNoise( float2 p, float period )
    {
        float2 cell = floor( p );
        float2 f = frac( p );
        f = f * f * ( 3 - 2 * f );
        float a = PlasmaHash( cell, period );
        float b = PlasmaHash( cell + float2( 1, 0 ), period );
        float c = PlasmaHash( cell + float2( 0, 1 ), period );
        float d = PlasmaHash( cell + 1, period );
        return lerp( lerp( a, b, f.x ), lerp( c, d, f.x ), f.y );
    }

    #if ( S_MODE_DEPTH == 0 )
        [earlydepthstencil]
    #endif
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        float time = g_flTime;
        // Object height makes positive rise speed travel UP, independently of the authored V direction.
        // The three chambers have different heights, but share a continuous flow in inches.
        float2 flow = float2( i.vTextureCoords.x, -i.vPositionOs.z / max( g_flFlowHeight, 1 ) );
        flow += float2( -g_flSwirlSpeed, g_flRiseSpeed ) * time;

        // Two gently changing, periodic curls deform the field, rather than sliding a flat image rigidly.
        float angle = flow.x * 6.2831853;
        float2 curl = float2(
            sin( angle + flow.y * 3.8 + time * .17 ) + .4 * sin( angle * 2 - flow.y * 2.1 - time * .11 ),
            .65 * cos( angle - flow.y * 3.2 + time * .13 ) );
        flow += curl * g_flWarp;

        float broad = PlasmaNoise( flow * float2( 3, 2 ), 6 );
        float secondary = PlasmaNoise( flow * float2( 6, 4 ) + float2( 1.9, 3.7 ), 12 );
        float hot = smoothstep( .27, .76, broad * .68 + secondary * .32 );

        float3 detailA = g_tColor.Sample( PlasmaSampler, flow ).rgb;
        float3 detailB = g_tColor.Sample( PlasmaSampler, flow * float2( 2, 1.6 )
            + float2( .31, -time * .006 ) ).rgb;
        float3 detail = lerp( detailA, detailB, .3 );
        float filament = smoothstep( .15, .72, detail.g ) * ( .4 + .6 * hot );
        float3 colour = lerp( float3( .34, .025, .002 ), float3( 1, .32, .025 ), hot );
        // Keep moving fine turbulence inside the broader pockets; a smooth heat field alone looked too waxy.
        colour = lerp( colour, detail * float3( 1, 1.1, .8 ), .35 );
        colour = lerp( colour, float3( 1.15, .74, .2 ), filament * .7 );
        colour *= .65 + .65 * detail.r;
        float shade = lerp( 1, .18 + .82 * hot, g_flDarkAreas );

        // Two long, non-matching periods keep the small pulse from looking like a flashing warning light.
        float pulse = 1 + g_flPulseAmount * ( .65 * sin( time * .54 ) + .35 * sin( time * .83 + 1.3 ) );
        m.Albedo = colour * .035;
        m.Emission = colour * shade * g_flBrightness * pulse;
        m.Normal = normalize( i.vNormalWs.xyz );
        m.Roughness = .9;
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        m.Opacity = 1;
        return ShadingModelStandard::Shade( i, m );
    }
}
