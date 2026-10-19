HEADER
{
    Description = "Spillway aerated torrents, advected whitewater and impact spray";
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"
    BoolAttribute( DoNotCastShadows, true );
    RenderState( DepthWriteEnable, false );
    RenderState( DepthEnable, true );
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( CullMode, NONE );

    CreateInputTexture2D( TextureTurbulence, Linear, 8, "", "_color", "Whitewater turbulence", Default3( .5, .5, .5 ) );
    Texture2D g_tTurbulence < Channel( RGB, Box( TextureTurbulence ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState WaterSampler < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    float g_flFoam < Default( 0 ); Range( 0, 2 ); >;
    float g_flSkyScatter < Default( .30 ); Range( 0, .5 ); >;
    float g_flMistDensity < Default( .52 ); Range( 0, 1 ); >;

    float Hash( float2 cell )
    {
        cell -= floor( cell / 128 ) * 128;
        uint2 q = asuint( int2( cell ) );
        uint h = q.x * 0x8DA6B343u ^ q.y * 0xD8163841u;
        h ^= h >> 15; h *= 0x2C1B3C6Du;
        h ^= h >> 12; h *= 0x297A2D39u;
        h ^= h >> 15;
        return float( h & 0x00FFFFFFu ) * ( 1.0 / 16777216.0 );
    }
    float Noise( float2 p )
    {
        float2 a = floor( p ), f = frac( p );
        f = f * f * ( 3 - 2 * f );
        return lerp( lerp( Hash( a ), Hash( a + float2( 1, 0 ) ), f.x ),
                     lerp( Hash( a + float2( 0, 1 ) ), Hash( a + 1 ), f.x ), f.y );
    }
    // Positive phase advects every pattern toward decreasing world Z. Wrap at
    // the hash period before adding position to retain precision in long sessions.
    float FallingZ( float z, float scale, float t, float speed )
    {
        return z / scale + frac( t * ( speed / scale ) / 128 ) * 128;
    }
    // A generated texture need not match its opposite borders pixel for pixel.
    // Crossfade to half-tile-offset samples where a border approaches; each
    // offset's own border is hidden by the other sample. Preserve UV derivatives.
    float Density( float2 p )
    {
        float2 dx = ddx( p ), dy = ddy( p );
        float2 f = frac( p );
        float2 w = smoothstep( .15, .42, abs( f - .5 ) );
        float a = g_tTurbulence.SampleGrad( WaterSampler, f, dx, dy ).r;
        float b = g_tTurbulence.SampleGrad( WaterSampler, f + float2( .5, 0 ), dx, dy ).r;
        float c = g_tTurbulence.SampleGrad( WaterSampler, f + float2( 0, .5 ), dx, dy ).r;
        float d = g_tTurbulence.SampleGrad( WaterSampler, f + .5, dx, dy ).r;
        return lerp( lerp( a, b, w.x ), lerp( c, d, w.x ), w.y );
    }
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        float3 world = m.WorldPosition;
        float2 uv = i.vTextureCoords.xy;
        float t = g_flTime;
        float3 foamColor = float3( .78, .83, .84 );
        m.Metalness = 0;
        m.Transmission = 0;
        m.AmbientOcclusion = 1;

        if ( g_flFoam > 1.5 )
        {
            float2 p = float2( world.y / 370, world.z / 420 - frac( t * .055 / 128 ) * 128 );
            float curl = Noise( p * .6 + 13.7 );
            p.x += ( curl - .5 ) * 1.4;
            float cloud = Noise( p ) * .65 + Noise( p * 2 + 7.1 ) * .25 + Noise( p * 4 + .7 ) * .10;
            float2 q = ( uv - .5 ) * 2;
            float rim = pow( saturate( 1 - dot( q, q ) ), 1.35 );
            m.Albedo = foamColor;
            m.Emission = foamColor * g_flSkyScatter;
            m.Normal = i.vNormalWs;
            m.Roughness = 1;
            m.Opacity = rim * smoothstep( .20, .72, cloud ) * g_flMistDensity;
            return ShadingModelStandard::Shade( i, m );
        }
        if ( g_flFoam > .5 )
        {
            // Plan -north is world -X: surface foam travels down the tailrace.
            float2 p = world.xy / float2( 510, 460 );
            p.x += frac( t * ( 145.0 / 510 ) );
            float curl = Noise( world.xy / 430 + 17.3 );
            p += float2( curl - .5, Noise( world.xy / 260 + 2.7 ) - .5 ) * .24;
            float density = Density( p );
            float foam = smoothstep( .12, .76, density );
            float2 q = ( uv - .5 ) * 2;
            float rim = pow( saturate( 1 - dot( q, q ) ), .7 );
            m.Albedo = foamColor * lerp( .62, 1, density );
            m.Emission = m.Albedo * g_flSkyScatter;
            m.Normal = normalize( i.vNormalWs + float3( ( density - .5 ) * .12, ( curl - .5 ) * .12, 0 ) );
            m.Roughness = .62;
            m.Opacity = rim * foam * .94;
            return ShadingModelStandard::Shade( i, m );
        }

        float progress = saturate( ( 2302 - world.z ) / 2582 );
        float2 broad = float2( world.y / 300, FallingZ( world.z, 640, t, 650 ) );
        float billow = Noise( broad );
        float edgeNoise = Noise( float2( world.y / 110, FallingZ( world.z, 190, t, 760 ) ) + 9.3 );
        float2 flowUv = float2( world.y / 940, FallingZ( world.z, 1100, t, 650 ) );
        flowUv.x += ( billow - .5 ) * .26;
        float primary = Density( flowUv );
        float secondary = Density( float2( world.y / 330 + 17.3, FallingZ( world.z, 420, t, 760 ) ) );
        float flow = primary * .56 + secondary * .16 + billow * .28;
        // Clear dark folds at the crest become aerated, broken whitewater below.
        float threshold = lerp( .64, .32, smoothstep( .00, .65, progress ) );
        float foam = smoothstep( threshold - .22, threshold + .24, flow );
        float fine = smoothstep( .50, .88, secondary );
        float border = min( uv.x, 1 - uv.x );
        float edge = smoothstep( .002, .035, border - ( edgeNoise - .36 ) * lerp( .015, .14, progress ) );
        float volumeShade = lerp( .78, 1.07, billow ) * lerp( .87, 1.08, fine );
        m.Albedo = lerp( float3( .035, .066, .077 ), foamColor * volumeShade, foam );
        m.Normal = normalize( i.vNormalWs + float3( ( primary - .5 ) * .20, ( secondary - .5 ) * .06, ( billow - .5 ) * .06 ) );
        m.Roughness = lerp( .14, .62, foam );
        // Aerated water scatters daylight through its volume, including the
        // dam's shaded face. Keep dark folds shaded and reserve fill for bubbles.
        m.Emission = m.Albedo * ( .035 + foam * g_flSkyScatter );
        m.Opacity = edge * lerp( .85, .995, foam );
        return ShadingModelStandard::Shade( i, m );
    }
}
