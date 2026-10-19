HEADER
{
    Description = "Belltower scanned stone: shallow parallax relief at physical scale";
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
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    CreateInputTexture2D( TextureHeight, Linear, 8, "", "_height", "Relief,20/10", Default( 1 ) );
    Texture2D g_tHeight < Channel( R, Box( TextureHeight ), Linear ); OutputFormat( ATI1N ); SrgbRead( false ); >;
    float2 g_vStoneUvScale < Default2( 1, 1 ); UiGroup( "Relief,20/20" ); >;
    float g_flReliefDepth < Default( .8 ); Range( 0, 4 ); UiGroup( "Relief,20/30" ); >;
    float g_flStoneRoughness < Default( 1 ); Range( .5, 2 ); UiGroup( "Relief,20/40" ); >;
    float g_flStoneRoughnessMin < Default( .55 ); Range( 0, 1 ); UiGroup( "Relief,20/45" ); >;
    float2 g_vReliefFade < Default2( 700, 1800 ); UiGroup( "Relief,20/50" ); >;
    // These controls default to the original response for the street material.
    float g_flStoneSaturation < Default( 1 ); Range( 0, 1 ); UiGroup( "Weathering,30/10" ); >;
    float g_flStoneAoStrength < Default( 1 ); Range( 0, 1 ); UiGroup( "Weathering,30/20" ); >;
    float g_flStoneMacroStrength < Default( 0 ); Range( 0, .3 ); UiGroup( "Weathering,30/30" ); >;

    float StoneHash( int3 cell )
    {
        uint3 q = asuint( cell );
        uint h = q.x * 0x8DA6B343u ^ q.y * 0xD8163841u ^ q.z * 0xCB1AB31Fu;
        h ^= h >> 15; h *= 0x2C1B3C6Du;
        h ^= h >> 12; h *= 0x297A2D39u; h ^= h >> 15;
        return float( h & 0x00FFFFFFu ) / 16777216.0;
    }

    float StoneWeather( float3 p )
    {
        int3 cell = int3( floor( p ) );
        float3 f = frac( p );
        f = f * f * ( 3.0 - 2.0 * f );
        return lerp(
            lerp( lerp( StoneHash( cell ), StoneHash( cell + int3(1,0,0) ), f.x ),
                  lerp( StoneHash( cell + int3(0,1,0) ), StoneHash( cell + int3(1,1,0) ), f.x ), f.y ),
            lerp( lerp( StoneHash( cell + int3(0,0,1) ), StoneHash( cell + int3(1,0,1) ), f.x ),
                  lerp( StoneHash( cell + int3(0,1,1) ), StoneHash( cell + int3(1,1,1) ), f.x ), f.y ), f.z );
    }

    // White is the stone's crest at the mesh surface. Only the joints recess.
    // Preserve base derivatives for all samples, including after the ray march,
    // so discontinuities in the traced UV cannot select a blurry mip level.
    float2 TraceRelief( float2 uv, float2 dx, float2 dy, float2 ray, float facing )
    {
        int steps = (int)lerp( 28.0, 10.0, saturate( facing ) );
        float layer = 1.0 / steps;
        float2 delta = ray * layer;
        float2 at = uv;
        float depth = 0;
        float surface = 1.0 - g_tHeight.SampleGrad( TextureFiltering, at, dx, dy ).r;
        float previous = surface;
        [loop] for ( int n = 0; n < steps && depth < surface; ++n )
        {
            previous = surface - depth;
            at -= delta;
            depth += layer;
            surface = 1.0 - g_tHeight.SampleGrad( TextureFiltering, at, dx, dy ).r;
        }
        float after = surface - depth;
        float weight = saturate( after / min( after - previous, -.00001 ) );
        return lerp( at, at + delta, weight );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        #if !S_MODE_DEPTH
        float2 uv = i.vTextureCoords.xy * g_vStoneUvScale;
        float2 dx = ddx( uv ), dy = ddy( uv );
        float3 n = normalize( i.vNormalWs );
        float3 toCamera = g_vCameraPositionWs - m.WorldPosition;
        float distance = length( toCamera );
        float3 view = toCamera / max( distance, .001 );
        float facing = dot( view, n );
        float fade = 1.0 - smoothstep( g_vReliefFade.x, g_vReliefFade.y, distance );
        [branch] if ( fade > .001 && g_flReliefDepth > 0 && facing > .01 )
        {
            // UV gradients in world space make depth an inch measurement,
            // independent of mesh UV scale, mirrored faces or tangent handedness.
            float3 px = ddx( m.WorldPosition ), py = ddy( m.WorldPosition );
            float3 a = cross( py, n ), b = cross( n, px );
            float determinant = dot( px, a );
            if ( abs( determinant ) > 1e-10 )
            {
                float3 gu = ( dx.x * a + dy.x * b ) / determinant;
                float3 gv = ( dx.y * a + dy.y * b ) / determinant;
                float2 ray = float2( dot( view, gu ), dot( view, gv ) );
                ray *= g_flReliefDepth * fade / max( facing, .14 );
                uv = TraceRelief( uv, dx, dy, ray, facing );
            }
        }
        float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );
        float luminance = dot( color.rgb, float3( .2126, .7152, .0722 ) );
        m.Albedo = lerp( luminance.xxx, color.rgb, g_flStoneSaturation ) * g_flTintColor * i.vVertexColor.rgb;
        [branch] if ( g_flStoneMacroStrength > 0 )
        {
            // Continuous world-space variation, with no UV jumps at tile edges.
            float weather = StoneWeather( m.WorldPosition / 230.0 ) * .7
                          + StoneWeather( m.WorldPosition / 83.0 + 19.3 ) * .3;
            m.Albedo *= 1.0 + ( weather * 2.0 - 1.0 ) * g_flStoneMacroStrength;
        }
        m.Normal = TransformNormal( DecodeNormal( normal.xyz ), i.vNormalWs, i.vTangentUWs, i.vTangentVWs );
        m.Roughness = max( g_flStoneRoughnessMin, pow( max( rma.r, .05 ), g_flStoneRoughness ) );
        m.AmbientOcclusion = lerp( 1.0, rma.b, g_flStoneAoStrength );
        m.TintMask = normal.a;
        m.TextureCoords = uv;
        #endif
        m.Metalness = 0;
        m.Transmission = 0;
        m.Opacity = 1;
        return ShadingModelStandard::Shade( i, m );
    }
}
