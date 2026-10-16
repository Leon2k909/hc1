HEADER
{
    Description = "A lamp's beam through hazy night air (Riverside's searchlight): single scattering off the haze in a cone of light, ray-marched through a closed proxy cone. Soft across the beam, fading as one over the distance squared from the lamp, brighter looking up the beam (forward scattering), with drifting haze, and ending where it meets anything";
}
MODES
{
    VrForward();
}
FEATURES
{
    #include "common/features.hlsl"
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
    PixelInput MainVs( VertexInput i )
    {
        PixelInput o = ProcessVertex( i );
        return FinalizeVertex( o );
    }
}
PS
{
    #include "common/pixel.hlsl"
    #include "common/classes/Depth.hlsl"
    #include "common/classes/Fog.hlsl"

    // The proxy is only where to shade: the light is worked out along the eye's ray and clipped at the opaque scene's depth,
    // so no depth test. Each pixel is shaded once, on the proxy's far side (see MainPs).
    BoolAttribute( translucent, true );
    RenderState( DepthEnable, false );
    RenderState( DepthWriteEnable, false );
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, ONE );
    RenderState( DstBlend, ONE );
    RenderState( CullMode, NONE );

    float3 g_vBeamColour < UiType( Color ); Default3( 0.8, 0.85, 1.0 ); UiGroup( "Beam,10/10" ); >;
    // How bright the beam looks side on just past the lens; it falls off as the light spreads.
    float g_flBeamIntensity < Default( 0.2 ); Range( 0.0, 10.0 ); UiGroup( "Beam,10/20" ); >;
    // Henyey-Greenstein asymmetry of the haze: 0 scatters evenly, haze and mist are about 0.5-0.8 (brighter looking up the beam).
    float g_flPhaseG < Default( 0.55 ); Range( 0.0, 0.95 ); UiGroup( "Beam,10/30" ); >;
    // The haze's lumpiness (0 even), the size of its lumps in inches, and how fast it drifts in inches a second.
    float g_flHazeDetail < Default( 0.35 ); Range( 0.0, 1.0 ); UiGroup( "Beam,10/40" ); >;
    float g_flHazeScale < Default( 140.0 ); Range( 1.0, 2000.0 ); UiGroup( "Beam,10/50" ); >;
    float g_flHazeDrift < Default( 6.0 ); Range( 0.0, 200.0 ); UiGroup( "Beam,10/60" ); >;
    // The pool it throws: how bright the lit surface is (irradiance relative to the lens's, times albedo), and the albedo
    // assumed for whatever it lands on (the map's mud and timber).
    float g_flPoolIntensity < Default( 30.0 ); Range( 0.0, 1000.0 ); UiGroup( "Pool,15/10" ); >;
    float3 g_vPoolAlbedo < UiType( Color ); Default3( 0.32, 0.25, 0.18 ); UiGroup( "Pool,15/20" ); >;

    // The cone in world space: its apex (the lamp's virtual source behind the lens), its axis, where the light leaves the lens
    // and where the proxy ends (inches along the axis from the apex), the beam's half angle (degrees, where it falls to 1/e^2)
    // and the proxy's half angle, past which nothing is drawn.
    float3 g_vBeamApex < Default3( 0.0, 0.0, 0.0 ); UiGroup( "Cone,20/10" ); >;
    float3 g_vBeamAxis < Default3( 1.0, 0.0, 0.0 ); UiGroup( "Cone,20/20" ); >;
    float g_flBeamStart < Default( 100.0 ); Range( 0.0, 100000.0 ); UiGroup( "Cone,20/30" ); >;
    float g_flBeamEnd < Default( 2000.0 ); Range( 0.0, 100000.0 ); UiGroup( "Cone,20/40" ); >;
    float g_flBeamHalfAngle < Default( 4.5 ); Range( 0.1, 60.0 ); UiGroup( "Cone,20/50" ); >;
    float g_flBeamOuterAngle < Default( 7.5 ); Range( 0.1, 80.0 ); UiGroup( "Cone,20/60" ); >;

    float Hash( float3 p )
    {
        p = frac( p * 0.3183099 + 0.1 );
        p *= 17.0;
        return frac( p.x * p.y * p.z * ( p.x + p.y + p.z ) );
    }

    float Noise( float3 x )
    {
        float3 i = floor( x );
        float3 f = frac( x );
        f = f * f * ( 3.0 - 2.0 * f );
        return lerp( lerp( lerp( Hash( i ), Hash( i + float3( 1, 0, 0 ) ), f.x ),
                           lerp( Hash( i + float3( 0, 1, 0 ) ), Hash( i + float3( 1, 1, 0 ) ), f.x ), f.y ),
                     lerp( lerp( Hash( i + float3( 0, 0, 1 ) ), Hash( i + float3( 1, 0, 1 ) ), f.x ),
                           lerp( Hash( i + float3( 0, 1, 1 ) ), Hash( i + float3( 1, 1, 1 ) ), f.x ), f.y ), f.z );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float2 screen = i.vPositionSs.xy;
        float3 origin = g_vCameraPositionWs;
        float3 worldPosition = i.vPositionWithOffsetWs + g_vHighPrecisionLightingOffsetWs.xyz;
        float3 ray = normalize( worldPosition - origin );

        // The proxy is a closed convex cone with outward normals: shade only where the ray leaves it, so every pixel it covers
        // is shaded once, from outside or inside it.
        if ( dot( i.vNormalWs, ray ) < 0.0 )
            discard;

        float3 axis = normalize( g_vBeamAxis );
        float3 fromApex = origin - g_vBeamApex;
        float cosOuter = cos( radians( g_flBeamOuterAngle ) );
        float c2 = cosOuter * cosOuter;
        float rayAlong = dot( ray, axis );
        float eyeAlong = dot( fromApex, axis );

        // Where the ray is inside the proxy's cone: ( (p - apex).axis )^2 >= cos^2 |p - apex|^2, a quadratic in t.
        float qa = rayAlong * rayAlong - c2;
        float qb = 2.0 * ( rayAlong * eyeAlong - dot( ray, fromApex ) * c2 );
        float qc = eyeAlong * eyeAlong - dot( fromApex, fromApex ) * c2;
        float t0 = -1e7;
        float t1 = 1e7;
        if ( abs( qa ) < 1e-6 )
        {
            if ( abs( qb ) > 1e-6 )
            {
                if ( qb > 0.0 ) t0 = -qc / qb; else t1 = -qc / qb;
            }
            else if ( qc < 0.0 )
                discard;
        }
        else
        {
            float disc = qb * qb - 4.0 * qa * qc;
            if ( disc < 0.0 )
            {
                if ( qa < 0.0 ) discard;
            }
            else
            {
                float s = sqrt( disc );
                float r0 = ( -qb - s ) / ( 2.0 * qa );
                float r1 = ( -qb + s ) / ( 2.0 * qa );
                float lo = min( r0, r1 );
                float hi = max( r0, r1 );
                if ( qa < 0.0 ) { t0 = lo; t1 = hi; }
                else if ( rayAlong > 0.0 ) t0 = hi;
                else t1 = lo;
            }
        }
        // From the lens to the proxy's end, which also keeps it to the cone in front of the apex.
        if ( abs( rayAlong ) > 1e-6 )
        {
            float s0 = ( g_flBeamStart - eyeAlong ) / rayAlong;
            float s1 = ( g_flBeamEnd - eyeAlong ) / rayAlong;
            t0 = max( t0, min( s0, s1 ) );
            t1 = min( t1, max( s0, s1 ) );
        }
        else if ( eyeAlong < g_flBeamStart || eyeAlong > g_flBeamEnd )
            discard;

        // Up to whatever opaque the ray meets: the ground the beam lands on, a wall, a zombie.
        bool hasSurface = Depth::GetNormalized( screen ) > 0.0;
        float3 surface = hasSurface ? Depth::GetWorldPosition( screen ) : origin + ray * 1e7;
        float sceneDistance = hasSurface ? max( 0.0, dot( surface - origin, ray ) ) : 1e7;
        t0 = max( t0, 0.0 );
        t1 = min( t1, sceneDistance );

        float tanCore = tan( radians( g_flBeamHalfAngle ) );
        float invCore2 = 1.0 / ( tanCore * tanCore );
        float start2 = g_flBeamStart * g_flBeamStart;
        float3 colour = 0.0;

        // Single scattering, marched with a per-pixel offset so the steps don't band.
        if ( t1 > t0 )
        {
            const int steps = 24;
            float dt = ( t1 - t0 ) / steps;
            float jitter = frac( 52.9829189 * frac( dot( screen, float2( 0.06711056, 0.00583715 ) ) ) );
            float g = g_flPhaseG;
            float hg90 = ( 1.0 - g * g ) / pow( 1.0 + g * g, 1.5 );
            float3 drift = float3( 0.6, -0.45, 0.25 ) * ( g_flTime * g_flHazeDrift / g_flHazeScale );
            float sum = 0.0;
            [loop]
            for ( int k = 0; k < steps; k++ )
            {
                float t = t0 + ( k + jitter ) * dt;
                float3 p = fromApex + ray * t;
                float along = max( dot( p, axis ), 1e-3 );
                float3 across = p - axis * along;
                // (tan of the angle off the axis / the beam's) squared; the profile is flat-topped with a soft edge.
                float q = dot( across, across ) / ( along * along ) * invCore2;
                float profile = exp( -2.0 * pow( q, 1.25 ) );
                // One over the distance squared from the source, 1 at the lens.
                float spread = start2 / ( along * along + dot( across, across ) );
                // Scattered towards the eye: the light travels away from the apex, the eye looks back along the ray.
                float mu = dot( normalize( p ), -ray );
                float phase = ( 1.0 - g * g ) / pow( max( 1.0 + g * g - 2.0 * g * mu, 1e-4 ), 1.5 ) / hg90;
                float haze = 1.0 + g_flHazeDetail * ( Noise( ( g_vBeamApex + p ) / g_flHazeScale + drift ) * 2.0 - 1.0 );
                sum += profile * spread * phase * haze;
            }
            // Scaled so Intensity is the brightness side on just past the lens: the path across the beam there is ~lens radius wide.
            sum *= dt / ( g_flBeamStart * tanCore );
            // Looking up the beam into the lamp is blinding; held short of the whole screen washing out.
            colour = g_vBeamColour * g_flBeamIntensity * min( sum, 6.0 );
            // The scene's fog between the eye and the beam dims it as it dims everything else (its own colour isn't added again).
            float3 middle = origin + ray * ( 0.5 * ( t0 + t1 ) );
            colour = max( Fog::Apply( middle, screen, colour ) - Fog::Apply( middle, screen, float3( 0, 0, 0 ) ), 0.0 );
        }

        // The pool of light where the beam lands: whatever the eye sees inside the cone is lit by the lamp, Lambert on the
        // surface's normal (from the depth of the neighbouring pixels) over an assumed albedo. The engine's spot lights
        // can't do it: one this narrow lights nothing, and their falloff has died out by the ground 25 m away.
        if ( hasSurface )
        {
            float3 p = surface - g_vBeamApex;
            float along = dot( p, axis );
            if ( along > g_flBeamStart && along < g_flBeamEnd )
            {
                float3 across = p - axis * along;
                float q = dot( across, across ) / ( along * along ) * invCore2;
                float profile = exp( -2.0 * pow( q, 1.25 ) );
                float3 right = Depth::GetWorldPosition( screen + float2( 1.0, 0.0 ) ) - surface;
                float3 down = Depth::GetWorldPosition( screen + float2( 0.0, 1.0 ) ) - surface;
                float3 normal = normalize( cross( right, down ) );
                if ( dot( normal, origin - surface ) < 0.0 ) normal = -normal;
                float lit = saturate( dot( normal, -normalize( p ) ) );
                float3 pool = g_vBeamColour * g_vPoolAlbedo * ( g_flPoolIntensity * profile * lit * start2 / dot( p, p ) );
                colour += max( Fog::Apply( surface, screen, pool ) - Fog::Apply( surface, screen, float3( 0, 0, 0 ) ), 0.0 );
            }
        }
        if ( all( colour <= 0.0 ) )
            discard;
        return float4( colour, 1.0 );
    }
}
