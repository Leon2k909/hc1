HEADER
{
    Description = "Lowtide granite: nine-millimetre joints, rounded arrises and distance-limited relief";
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
    CreateInputTexture2D( TextureHeight, Linear, 8, "", "_height", "Paving", Default( 1 ) );
    Texture2D g_tHeight < Channel( R, Box( TextureHeight ), Linear ); OutputFormat( ATI1N ); SrgbRead( false ); >;
    float4 g_vPavingRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Paving" ); >;
    float2 g_vPavingScale < Default2( 1, 1 ); UiGroup( "Paving" ); >;
    float g_flReliefDepth < Default( .35433071 ); Range( 0, 1 ); UiGroup( "Paving" ); >;
    float2 g_vReliefFade < Default2( 300, 850 ); UiGroup( "Paving" ); >;

    float2 AtlasUv( float2 repeat )
    {
        return g_vPavingRegion.xy + frac( repeat ) * g_vPavingRegion.zw;
    }

    float PavingDepth( float2 repeat, float2 dx, float2 dy )
    {
        return 1 - g_tHeight.SampleGrad( TextureFiltering, AtlasUv( repeat ), dx, dy ).r;
    }

    float2 TracePaving( float2 repeat, float2 dx, float2 dy, float2 ray, float facing )
    {
        int steps = (int)lerp( 24.0, 8.0, saturate( facing ) );
        float layer = 1.0 / steps;
        float2 delta = ray * layer;
        float2 at = repeat;
        float depth = 0;
        float surface = PavingDepth( at, dx, dy );
        float previous = surface;
        [loop] for ( int step = 0; step < steps && depth < surface; ++step )
        {
            previous = surface - depth;
            at -= delta;
            depth += layer;
            surface = PavingDepth( at, dx, dy );
        }
        float after = surface - depth;
        float weight = saturate( after / min( after - previous, -.00001 ) );
        return lerp( at, at + delta, weight );
    }

    float PavingNoise( float2 p )
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
        Material material = Material::Init( input );
        #if !S_MODE_DEPTH
        float2 repeat = input.vTextureCoords.xy * g_vPavingScale;
        float2 rx = ddx( repeat ), ry = ddy( repeat );
        // Every atlas sample uses derivatives from BEFORE frac and ray marching.
        float2 dx = rx * g_vPavingRegion.zw;
        float2 dy = ry * g_vPavingRegion.zw;
        float3 n = normalize( input.vNormalWs );
        float3 toCamera = g_vCameraPositionWs - material.WorldPosition;
        float distance = length( toCamera );
        float3 view = toCamera / max( distance, .001 );
        float facing = dot( view, n );
        float fade = 1 - smoothstep( g_vReliefFade.x, g_vReliefFade.y, distance );
        // Evaluate the derivatives outside divergent control flow. This basis
        // respects existing mirrored UVs and measures depth in engine inches.
        float3 px = ddx( material.WorldPosition ), py = ddy( material.WorldPosition );
        float3 a = cross( py, n ), b = cross( n, px );
        float determinant = dot( px, a );
        [branch] if ( fade > .001 && g_flReliefDepth > 0 && facing > .01 && abs( determinant ) > 1e-10 )
        {
            float3 gu = ( rx.x * a + ry.x * b ) / determinant;
            float3 gv = ( rx.y * a + ry.y * b ) / determinant;
            float2 ray = float2( dot( view, gu ), dot( view, gv ) );
            ray *= g_flReliefDepth * fade / max( facing, .16 );
            // Suppress subpixel relief before it can sparkle in distant views.
            float pixels = length( ray / max( abs( rx ) + abs( ry ), .00001 ) );
            float resolved = smoothstep( .35, 1.25, pixels );
            [branch] if ( resolved > .001 )
                repeat = TracePaving( repeat, dx, dy, ray * resolved, facing );
        }
        float2 uv = AtlasUv( repeat );
        float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );
        material.Albedo = color.rgb * g_flTintColor * input.vVertexColor.rgb;
        material.Normal = TransformNormal( DecodeNormal( normal.xyz ), input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
        float2 ground = material.WorldPosition.xy;
        float broad = PavingNoise( ground / 230 );
        float patches = broad * .65 + PavingNoise( ground / 61 + 10.3 ) * .35;
        float wet = smoothstep( .44, .72, patches );
        material.Albedo *= lerp( .91, 1.02, PavingNoise( ground / 390 + 9 ) );
        material.Albedo *= lerp( 1, .52, wet );
        material.Roughness = lerp( rma.r, max( .23, rma.r * .38 ), wet );
        material.AmbientOcclusion = rma.b;
        material.TintMask = normal.a;
        material.TextureCoords = uv;
        #endif
        material.Metalness = 0;
        material.Transmission = 0;
        material.Opacity = 1;
        return ShadingModelStandard::Shade( input, material );
    }
}
