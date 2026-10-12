HEADER
{
    Description = "A turning two-blade prop as the eye or a camera sees it: each point of its disc covered for the share of the time a blade is over it. A smaller prop of the same shape is drawn scaled (RotorScale)";
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
    // The disc turns with its rotor: its own x is blade one, its z the axis. Taken from the disc as drawn, so the
    // pattern can't lag the hub when the drone moves fast.
    float3 vPositionOs : TEXCOORD8;
    float3 vBladeWs : TEXCOORD9;
    float3 vAxisWs : TEXCOORD10;
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i )
    {
        PixelInput o = ProcessVertex( i );
        float3x4 m = GetTransformMatrix( i.nInstanceTransformID );
        o.vPositionOs = i.vPositionOs.xyz;
        o.vBladeWs = float3( m[0][0], m[1][0], m[2][0] );
        o.vAxisWs = float3( m[0][2], m[1][2], m[2][2] );
        return FinalizeVertex( o );
    }
}
PS
{
    #include "common/pixel.hlsl"
    BoolAttribute( translucent, true );
    RenderState( DepthWriteEnable, false );
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( CullMode, DEFAULT );

    // Set each frame by ReconRotor:
    //   RotorSpin   +1 turning anticlockwise seen from above (from the disc's +z), -1 clockwise
    //   RotorTrail  how far back the eye still sees a blade it's following, radians of turn
    //   RotorFusion 0 while separate blades show, 1 once the eye can't follow them (blade passes over ~50 a second)
    //   RotorScale  the octocopter's prop radius over this rotor's: a smaller rotor of the same shape (the nano
    //               drone's, Tools/build_recon_nano.py) is drawn as the octocopter's scaled down
    //   RotorYoke   1 where the blades fold on a yoke (the octocopter's), 0 where they don't (the nano's)
    float g_flRotorSpin < Attribute( "RotorSpin" ); Default( 1.0 ); >;
    float g_flRotorTrail < Attribute( "RotorTrail" ); Default( 0.03 ); >;
    float g_flRotorFusion < Attribute( "RotorFusion" ); Default( 1.0 ); >;
    float g_flRotorScale < Attribute( "RotorScale" ); Default( 1.0 ); >;
    float g_flRotorYoke < Attribute( "RotorYoke" ); Default( 1.0 ); >;

    // The disc's model is in inches.
    static const float InchesToMetres = 0.0254;

    // The prop (Tools/build_recon_octocopter.py), metres: radius, pitch, and the hub that's drawn solid.
    static const float PropRadius = 0.330;
    static const float PropPitch = 0.22;
    static const float HubRadius = 0.024;
    // The two arms of the yoke the blades fold on: out to 0.052, 27 mm wide and 16 mm deep.
    static const float YokeEnd = 0.052;
    static const float YokeHalfWidth = 0.0135;
    static const float YokeHalfDepth = 0.0078;
    static const float Pi = 3.14159265;

    // The blade's chord along its length (blade_chord), with the rounded tip (tip_round).
    float Chord( float r )
    {
        float s = r / PropRadius;
        float c;
        if ( s < 0.16 ) c = lerp( 0.026, 0.044, saturate( ( s - 0.10 ) / 0.06 ) );
        else if ( s < 0.26 ) c = lerp( 0.044, 0.050, ( s - 0.16 ) / 0.10 );
        else if ( s < 0.45 ) c = lerp( 0.050, 0.046, ( s - 0.26 ) / 0.19 );
        else if ( s < 0.70 ) c = lerp( 0.046, 0.036, ( s - 0.45 ) / 0.25 );
        else if ( s < 0.88 ) c = lerp( 0.036, 0.027, ( s - 0.70 ) / 0.18 );
        else c = lerp( 0.027, 0.020, saturate( ( s - 0.88 ) / 0.12 ) );
        float u = saturate( 1.0 - ( PropRadius - r ) / 0.014 );
        return c * sqrt( saturate( 1.0 - u * u ) );
    }

    // The share of the time a point delta radians behind blade one is under a blade h either side of it, as the eye
    // keeps what it saw fading over trail radians of turn; two blades, pi apart.
    float Coverage( float delta, float h, float trail )
    {
        float k = 1.0 / trail;
        float now = exp( -max( delta - h, 0.0 ) * k ) - exp( -( delta + h ) * k );
        float later = exp( -( delta + Pi - h ) * k ) * ( 1.0 - exp( -2.0 * h * k ) ) / max( 1.0 - exp( -Pi * k ), 1e-4 );
        return now + later;
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float3 world = i.vPositionWithOffsetWs + g_vCameraPositionWs;
        float3 A = normalize( i.vAxisWs );
        float spin = g_flRotorSpin >= 0.0 ? 1.0 : -1.0;
        float3 F = normalize( i.vBladeWs - A * dot( i.vBladeWs, A ) );
        float3 L = cross( A, F );

        float scale = max( g_flRotorScale, 0.01 );
        float x = i.vPositionOs.x * InchesToMetres * scale, y = i.vPositionOs.y * InchesToMetres * scale;
        float r = length( float2( x, y ) );
        if ( r < HubRadius || r > PropRadius ) discard;

        float3 around = ( -y * F + x * L ) / r;
        float3 V = normalize( g_vCameraPositionWs - world );
        float faceOn = max( abs( dot( A, V ) ), 0.05 );

        // How far behind blade one this point is, the way it turns, in [-h, pi - h). The blade's line bends forward
        // along its middle and sweeps back at the tip.
        float phi = atan2( y, x );
        float s = r / PropRadius;
        float sweep = 0.010 * sin( Pi * saturate( ( s - 0.12 ) / 0.88 ) ) - 0.028 * pow( saturate( ( s - 0.62 ) / 0.38 ), 2.0 );
        float delta = -spin * phi + sweep / r;

        // The blade, twisted to its pitch, seen from here: tipped towards the eye it covers more of the disc.
        float pitch = atan( PropPitch / ( 2.0 * Pi * max( r, 0.055 ) ) );
        float3 bladeNormal = cos( pitch ) * A - spin * sin( pitch ) * around;
        if ( dot( bladeNormal, V ) < 0.0 ) bladeNormal = -bladeNormal;
        float h = Chord( r ) / ( 2.0 * r );
        h = min( h * abs( dot( bladeNormal, V ) ) / faceOn, Pi * 0.5 - 0.01 );

        delta = delta + h;
        delta = delta - Pi * floor( delta / Pi );
        delta = delta - h;

        float trail = max( g_flRotorTrail, 0.03 );
        float even = 2.0 * h / Pi;
        float blade = lerp( Coverage( delta, h, trail ), even, saturate( g_flRotorFusion ) );

        // The yoke's arms, a box section turning with the blades: always fused, as they're near the axis.
        float yoke = 0.0;
        if ( g_flRotorYoke > 0.5 && r < YokeEnd )
        {
            float hy = ( YokeHalfWidth * abs( dot( A, V ) ) + YokeHalfDepth * abs( dot( around, V ) ) ) / faceOn / r;
            hy = min( hy, Pi * 0.5 - 0.01 );
            float yokeDelta = delta + hy;
            yokeDelta = yokeDelta - Pi * floor( yokeDelta / Pi ) - hy;
            yoke = lerp( Coverage( yokeDelta, hy, trail ), 2.0 * hy / Pi, saturate( g_flRotorFusion ) );
            yoke *= 1.0 - smoothstep( YokeEnd - 0.004, YokeEnd, r );
        }

        float alpha = saturate( max( blade, yoke ) );
        // A disc is never quite solid: the blades' edges are thin and the light gets round them.
        alpha = min( alpha, 0.9 );
        // Soft at the root, where the solid hub takes over.
        alpha *= smoothstep( HubRadius, HubRadius + 0.003, r );
        if ( alpha <= 0.002 ) discard;

        // Matte carbon composite, lit as the blade is where it passes: the sun glints off it along a radius.
        Material m = Material::From( i );
        bool onYoke = yoke > blade;
        m.Albedo = onYoke ? float3( 0.035, 0.035, 0.037 ) : float3( 0.028, 0.028, 0.030 );
        m.Normal = onYoke ? ( dot( A, V ) >= 0.0 ? A : -A ) : bladeNormal;
        m.Roughness = onYoke ? 0.45 : 0.38;
        m.Metalness = 0.0;
        m.AmbientOcclusion = 1;
        m.Opacity = 1;
        float3 colour = ShadingModelStandard::Shade( i, m ).rgb;
        return float4( colour, alpha );
    }
}
