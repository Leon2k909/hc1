    float g_flReflectionFilter < Default( 0.08 ); Range( 0, 2 ); UiGroup( "Water" ); >;

    float3 FilteredPlanarReflection( float2 uv, float roughness )
    {
        uint width, height, levels;
        g_tWaterReflection.GetDimensions( 0, width, height, levels );
        float2 size = max( float2( width, height ), 1 );
        float2 dx = ddx( uv ) * size;
        float2 dy = ddy( uv ) * size;
        float footprint = max( length( dx ), length( dy ) );
        // Perceptual roughness squared is the microfacet slope parameter.
        // Project an approximate reflected cone into the capture's pixel scale.
        // The mip pyramid is a bounded box-filter approximation, not a full
        // view-dependent GGX convolution or a correction for reflection depth.
        float2 projection = abs( float2( g_matViewToProjection[0][0], g_matViewToProjection[1][1] ) );
        float cone = roughness * roughness * max( size.x * projection.x, size.y * projection.y );
        float diameter = max( footprint, cone * g_flReflectionFilter );
        float lod = clamp( log2( max( diameter, 1 ) ), 0, max( float( levels ) - 1, 0 ) );
        // An old one-level target remains valid during a guarded staged import.
        return g_tWaterReflection.SampleLevel( WaterReflectionSampler, uv, lod ).rgb;
    }
