// Lowtide candidate: view-dependent mortar depth in physical engine inches.
// Colour, normal and packed surface maps retain their existing registration.
CreateInputTexture2D( TextureHeight, Linear, 8, "", "_height", "Mortar", Default( 1 ) );
Texture2D g_tMortarHeight < Channel( R, Box( TextureHeight ), Linear ); OutputFormat( ATI1N ); SrgbRead( false ); >;
float g_flMortarDepth < Default( .19685039 ); Range( 0, .5 ); UiGroup( "Mortar" ); >;
float2 g_vMortarFade < Default2( 144, 512 ); UiGroup( "Mortar" ); >;

float MortarDepthAt( float2 uv, float2 dx, float2 dy )
{
    return 1 - g_tMortarHeight.SampleGrad( TextureFiltering, uv, dx, dy ).r;
}

float2 TraceMortar( float2 uv, float2 dx, float2 dy, float2 ray, float facing )
{
    // Sub-texel steps prevent a short exposed edge from being skipped entirely.
    // The height field is authored at 2048 square. Distance/subpixel gates keep
    // this extra work local to resolved close-range relief.
    int steps = (int)clamp( ceil( length( ray * 2048.0 ) * 2.0 ), 8.0, 64.0 );
    float layer = 1.0 / steps;
    float2 delta = ray * layer;
    float2 at = uv;
    float depth = 0;
    float surface = MortarDepthAt( at, dx, dy );
    float previous = surface;
    [loop] for ( int step = 0; step < steps && depth < surface; ++step )
    {
        previous = surface - depth;
        at -= delta;
        depth += layer;
        surface = MortarDepthAt( at, dx, dy );
    }
    float low = max( depth - layer, 0 ), high = depth;
    float before = previous, after = surface - depth;
    // Refine the crossing rather than allowing coarse layers to stair-step
    // along narrow joints when the player looks almost parallel to a wall.
    [unroll] for ( int refine = 0; refine < 3; ++refine )
    {
        float middle = ( low + high ) * .5;
        float offset = MortarDepthAt( uv - ray * middle, dx, dy ) - middle;
        if ( offset > 0 ) { low = middle; before = offset; }
        else { high = middle; after = offset; }
    }
    float weight = saturate( before / max( before - after, .00001 ) );
    return uv - ray * lerp( low, high, weight );
}

Material ReadReliefBrick( PixelInput input, float2 scale )
{
    Material material = Material::Init( input );
    #if !S_MODE_DEPTH
    float2 uv = input.vTextureCoords.xy * scale;
    // Keep the continuous original derivatives through wrapping and tracing.
    float2 dx = ddx( uv ), dy = ddy( uv );
    float3 n = normalize( input.vNormalWs );
    float3 toCamera = g_vCameraPositionWs - material.WorldPosition;
    float distance = length( toCamera );
    float3 view = toCamera / max( distance, .001 );
    float facing = dot( view, n );
    float fade = 1 - smoothstep( g_vMortarFade.x, g_vMortarFade.y, distance );
    float3 px = ddx( material.WorldPosition ), py = ddy( material.WorldPosition );
    float3 a = cross( py, n ), b = cross( n, px );
    float determinant = dot( px, a );
    [branch] if ( fade > .001 && g_flMortarDepth > 0 && facing > .01 && abs( determinant ) > 1e-10 )
    {
        // Screen derivatives recover world-space UV gradients. This works for
        // both orientations and mirrored UVs, without assuming tangent scale.
        float3 gu = ( dx.x * a + dy.x * b ) / determinant;
        float3 gv = ( dx.y * a + dy.y * b ) / determinant;
        float2 ray = float2( dot( view, gu ), dot( view, gv ) );
        ray *= g_flMortarDepth * fade / max( facing, .16 );
        float pixels = length( ray / max( abs( dx ) + abs( dy ), .00001 ) );
        float resolved = smoothstep( .35, 1.25, pixels );
        [branch] if ( resolved > .001 )
            uv = TraceMortar( uv, dx, dy, ray * resolved, facing );
    }
    float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
    float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
    float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );
    material.Albedo = color.rgb * g_flTintColor * input.vVertexColor.rgb;
    material.Normal = TransformNormal( DecodeNormal( normal.xyz ), input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
    material.Roughness = rma.r;
    material.AmbientOcclusion = rma.b;
    material.TintMask = normal.a;
    material.TextureCoords = uv;
    #endif
    material.Metalness = 0;
    material.Transmission = 0;
    material.Opacity = 1;
    return material;
}
