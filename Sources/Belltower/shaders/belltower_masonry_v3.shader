HEADER
{
    Description = "Belltower irregular limestone: matched color and height, recessed lime joints";
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
    CreateInputTexture2D( TextureStoneColor, Srgb, 8, "", "_color", "Masonry,10/10", Default3( .5, .48, .44 ) );
    CreateInputTexture2D( TextureStoneHeight, Linear, 8, "", "_height", "Masonry,10/20", Default( .75 ) );
    CreateInputTexture2D( TextureStoneSeams, Linear, 8, "", "_data", "Masonry,10/25", Default3( 0, 0, 0 ) );
    Texture2D g_tStoneColor < Channel( RGB, Box( TextureStoneColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tStoneHeight < Channel( R, Box( TextureStoneHeight ), Linear ); OutputFormat( ATI1N ); SrgbRead( false ); >;
    Texture2D g_tStoneSeams < Channel( RGB, Box( TextureStoneSeams ), Linear ); OutputFormat( RGBA8888 ); SrgbRead( false ); >;
    SamplerState MasonrySampler < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    SamplerState SeamSampler < Filter( POINT ); AddressU( WRAP ); AddressV( WRAP ); >;
    float2 g_vMasonryUvScale < Default2( .677333, .677333 ); UiGroup( "Masonry,10/30" ); >;
    float2 g_vMasonryQuiltShift < Default2( .37001595, .42982456 ); UiGroup( "Masonry,10/35" ); >;
    float3 g_vMasonryTint < Default3( 1.08, 1.08, 1.08 ); UiGroup( "Masonry,10/40" ); >;
    float g_flMasonryDepth < Default( .8 ); Range( 0, 2 ); UiGroup( "Masonry,10/50" ); >;
    float g_flMasonryNormal < Default( .75 ); Range( 0, 2 ); UiGroup( "Masonry,10/60" ); >;
    float g_flMasonrySaturation < Default( .72 ); Range( 0, 1 ); UiGroup( "Masonry,10/70" ); >;
    float g_flMasonryContrast < Default( .86 ); Range( .5, 1.5 ); UiGroup( "Masonry,10/80" ); >;
    float g_flMasonryWeather < Default( .18 ); Range( 0, .4 ); UiGroup( "Masonry,10/90" ); >;

    float StoneHash( int2 cell )
    {
        uint2 q = asuint( cell );
        uint h = q.x * 0x8DA6B343u ^ q.y * 0xD8163841u;
        h ^= h >> 15; h *= 0x2C1B3C6Du;
        h ^= h >> 12; h *= 0x297A2D39u; h ^= h >> 15;
        return float( h & 0x00FFFFFFu ) / 16777216.0;
    }
    float StoneNoise( float2 p )
    {
        int2 cell = int2( floor( p ) );
        float2 f = frac( p );
        f = f * f * ( 3.0 - 2.0 * f );
        return lerp( lerp( StoneHash( cell ), StoneHash( cell + int2(1,0) ), f.x ),
                     lerp( StoneHash( cell + int2(0,1) ), StoneHash( cell + 1 ), f.x ), f.y );
    }
    float2 StoneUv( float2 uv )
    {
        // Numerical selectors follow low-cost joins in the source PBR fields.
        // No mirrored stone shapes and no blended double mortar outlines.
        float2 offset = step( .5, g_tStoneSeams.SampleLevel( SeamSampler, uv, 0 ).rg );
        return uv + offset * g_vMasonryQuiltShift;
    }
    float Height( float2 uv, float2 dx, float2 dy )
    {
        // Keep the broad stone faces calm. Edge recesses supply the main shape;
        // generated color freckles are never treated as surface displacement.
        float h = g_tStoneHeight.SampleGrad( MasonrySampler, StoneUv( uv ), dx, dy ).r;
        return smoothstep( .16, .74, h );
    }
    float2 Relief( float2 uv, float2 dx, float2 dy, float2 ray, float facing )
    {
        int steps = (int)lerp( 18.0, 8.0, saturate( facing ) );
        float layer = 1.0 / steps;
        float2 delta = ray * layer, at = uv;
        float depth = 0;
        float surface = 1.0 - Height( at, dx, dy );
        float previous = surface;
        [loop] for ( int n = 0; n < steps && depth < surface; ++n )
        {
            previous = surface - depth;
            at -= delta;
            depth += layer;
            surface = 1.0 - Height( at, dx, dy );
        }
        float after = surface - depth;
        return lerp( at, at + delta, saturate( after / min( after - previous, -.00001 ) ) );
    }
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        #if !S_MODE_DEPTH
        float2 uv = i.vTextureCoords.xy * g_vMasonryUvScale;
        float2 dx = ddx( uv ), dy = ddy( uv );
        float3 n = normalize( i.vNormalWs );
        float3 px = ddx( m.WorldPosition ), py = ddy( m.WorldPosition );
        float3 a = cross( py, n ), b = cross( n, px );
        float determinant = dot( px, a );
        float3 gu = 0, gv = 0;
        if ( abs( determinant ) > 1e-10 )
        {
            gu = ( dx.x * a + dy.x * b ) / determinant;
            gv = ( dx.y * a + dy.y * b ) / determinant;
        }
        float3 toCamera = g_vCameraPositionWs - m.WorldPosition;
        float distance = length( toCamera );
        float3 view = toCamera / max( distance, .001 );
        float facing = dot( view, n );
        float fade = 1.0 - smoothstep( 600.0, 1400.0, distance );
        [branch] if ( fade > .001 && g_flMasonryDepth > 0 && facing > .01 )
        {
            float2 ray = float2( dot( view, gu ), dot( view, gv ) );
            ray *= g_flMasonryDepth * fade / max( facing, .14 );
            uv = Relief( uv, dx, dy, ray, facing );
        }
        float3 color = g_tStoneColor.SampleGrad( MasonrySampler, StoneUv( uv ), dx, dy ).rgb;
        float h = Height( uv, dx, dy );
        float luminance = dot( color, float3( .2126, .7152, .0722 ) );
        float stoneMean = g_tStoneSeams.SampleLevel( SeamSampler, uv, 0 ).b;
        float calm = lerp( luminance, stoneMean, smoothstep( .3, .8, h ) * .50 );
        color *= calm / max( luminance, .01 );
        luminance = dot( color, float3( .2126, .7152, .0722 ) );
        color = lerp( luminance.xxx, color, g_flMasonrySaturation );
        color = max( 0, ( color - .28 ) * g_flMasonryContrast + .28 );
        uint width, height;
        g_tStoneHeight.GetDimensions( width, height );
        float2 texel = 1.25 / float2( width, height );
        float du = ( Height( uv + float2(texel.x,0), dx, dy ) - Height( uv - float2(texel.x,0), dx, dy ) ) / ( 2 * texel.x );
        float dv = ( Height( uv + float2(0,texel.y), dx, dy ) - Height( uv - float2(0,texel.y), dx, dy ) ) / ( 2 * texel.y );
        m.Normal = normalize( n - ( du * gu + dv * gv ) * g_flMasonryDepth * g_flMasonryNormal );
        float side = abs( n.x ) > abs( n.y ) ? m.WorldPosition.y : m.WorldPosition.x;
        float2 wall = float2( side, m.WorldPosition.z );
        float weather = StoneNoise( wall / float2(270,190) ) * .7 + StoneNoise( wall / 83.0 + 19.3 ) * .3;
        float ground = m.WorldPosition.x < -1000 ? -48.0 : 0.0;
        if ( abs( m.WorldPosition.y ) >= 1850 && m.WorldPosition.x < -1000 )
            ground = -48 * saturate( ( -1000 - m.WorldPosition.x ) / 200.0 );
        float foot = exp( -max( 0, m.WorldPosition.z - ground ) / 18.0 );
        float damp = foot * smoothstep( .28, .76, weather ) * .12;
        m.Albedo = color * g_vMasonryTint * i.vVertexColor.rgb;
        m.Albedo *= 1 + ( weather * 2 - 1 ) * g_flMasonryWeather;
        m.Albedo *= lerp( float3(1,1,1), float3(.68,.73,.66), damp );
        m.Roughness = lerp( .94, .84, h );
        m.AmbientOcclusion = lerp( .90, 1.0, h );
        m.TextureCoords = uv;
        #endif
        m.Metalness = 0;
        m.Transmission = 0;
        m.Opacity = 1;
        return ShadingModelStandard::Shade( i, m );
    }
}
