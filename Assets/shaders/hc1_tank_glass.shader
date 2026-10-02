//=========================================================================================================================
// Reef Hall's tank glass (Tools/reefhall_map.py, materials/reefhall/rh_tank_glass*.vmat).
//
// The pane is the front of a tank full of water. Everything behind it (sand, rock, coral, fish, the tank's back wall) is
// opaque geometry already drawn, so the pane reads the frame and the depth behind it and puts the water in between:
//  - The water path is the distance from the pane to what's behind it. Light from behind loses each colour by
//    Beer-Lambert (red goes first), and the water's own light (what it scatters from the tank's lamps) takes its place.
//  - That light is brighter near the surface (g_flSurfaceZ) and darker towards the floor: g_vWaterScatter to
//    g_vWaterDeep over g_flDeepRange.
//  - Caustics: the surface's waves focus the light from above into a moving net on what's behind, fading with depth.
//  - Shafts: the same light caught in the water, marched in 8 steps along the view ray.
//  - The pane refracts a little (the water moving), reflects the room like glass, and goes green at a glancing angle,
//    as thick acrylic does.
// Absorption is kept low enough that a player on the far side of a walk-through tunnel stays easy to see.
// It casts no shadow (no Depth mode), so the tank's own lamps light its insides through the glass.
// A pane is one-sided, facing the room: from inside a tank (nobody goes there) it's culled. Where a pane looks right
// through a tank (a round one, past its rock), what's behind is the room, so the path is capped at g_flMaxWater, the
// tank's own depth.
//=========================================================================================================================
HEADER
{
    Description = "HC1 aquarium tank glass: water depth, absorption, caustics and light shafts behind the pane";
    Version = 1;
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
    #define BLEND_MODE_ALREADY_SET 1
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

    PixelInput MainVs( VS_INPUT i )
    {
        PixelInput o = ProcessVertex( i );
        return FinalizeVertex( o );
    }
}

PS
{
    #define DEPTH_STATE_ALREADY_SET 1
    #define BLEND_MODE_ALREADY_SET 1
    #define S_TRANSLUCENT 1

    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    #include "common/classes/Depth.hlsl"

    BoolAttribute( bWantsFBCopyTexture, true );

    Texture2D g_tFrameBufferCopyTexture < Attribute( "FrameBufferCopyTexture" ); SrgbRead( false ); >;

    // Per inch of water, per colour.
    float3 g_vWaterAbsorb < Default3( 0.0060, 0.0012, 0.0006 ); UiGroup( "Water,10/10" ); >;
    float g_flTurbidity < Default( 0.0006 ); Range( 0.0, 0.02 ); UiGroup( "Water,10/20" ); >;
    float3 g_vWaterScatter < UiType( Color ); Default3( 0.06, 0.38, 0.56 ); UiGroup( "Water,10/30" ); >;
    float3 g_vWaterDeep < UiType( Color ); Default3( 0.008, 0.07, 0.15 ); UiGroup( "Water,10/40" ); >;
    float g_flSurfaceZ < Default( 400.0 ); Range( -10000.0, 10000.0 ); UiGroup( "Water,10/50" ); >;
    float g_flDeepRange < Default( 320.0 ); Range( 16.0, 2000.0 ); UiGroup( "Water,10/60" ); >;
    float g_flMaxWater < Default( 2000.0 ); Range( 16.0, 10000.0 ); UiGroup( "Water,10/70" ); >;
    float g_flCaustics < Default( 0.9 ); Range( 0.0, 4.0 ); UiGroup( "Light,20/10" ); >;
    float g_flCausticScale < Default( 48.0 ); Range( 4.0, 400.0 ); UiGroup( "Light,20/20" ); >;
    float g_flShafts < Default( 0.35 ); Range( 0.0, 4.0 ); UiGroup( "Light,20/30" ); >;
    float g_flRefraction < Default( 0.0025 ); Range( 0.0, 0.02 ); UiGroup( "Glass,30/10" ); >;
    float g_flGlassRoughness < Default( 0.04 ); Range( 0.0, 1.0 ); UiGroup( "Glass,30/20" ); >;
    float3 g_vGlassEdge < UiType( Color ); Default3( 0.70, 0.86, 0.82 ); UiGroup( "Glass,30/30" ); >;

    // A tileable water caustic (Dave Hoskins' iteration): bright threads where the waves focus the light.
    float Caustic( float2 p, float t )
    {
        float2 q = p;
        float c = 1.0;
        const float inten = 0.005;
        [unroll]
        for ( int n = 0; n < 4; n++ )
        {
            float t2 = t * ( 1.0 - ( 3.5 / float( n + 1 ) ) );
            q = p + float2( cos( t2 - q.x ) + sin( t2 + q.y ), sin( t2 - q.y ) + cos( t2 + q.x ) );
            c += 1.0 / length( float2( p.x / ( sin( q.x + t2 ) / inten ), p.y / ( cos( q.y + t2 ) / inten ) ) );
        }
        c /= 4.0;
        c = 1.17 - pow( abs( c ), 1.4 );
        return saturate( pow( abs( c ), 8.0 ) );
    }

    // Soft bands of light coming down at a slant, drifting with the surface.
    float Shaft( float3 p, float t )
    {
        float down = max( g_flSurfaceZ - p.z, 0.0 );
        float2 q = p.xy + down * float2( 0.18, 0.11 );
        float s = sin( q.x * 0.021 + t * 0.21 ) * sin( q.y * 0.017 - t * 0.17 ) + 0.6 * sin( ( q.x + q.y ) * 0.011 + t * 0.09 );
        return pow( saturate( s * 0.7 ), 2.0 ) * exp( -down / ( g_flDeepRange * 1.4 ) );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float3 vNormal = normalize( i.vNormalWs );

        float3 vViewRayWs = normalize( i.vPositionWithOffsetWs.xyz );
        float flNDotV = saturate( dot( -vNormal, vViewRayWs ) );
        float3 vEnvBRDF = CalcBRDFReflectionFactor( flNDotV, g_flGlassRoughness, 0.04 );
        float t = g_flTime;

        // What's behind the pane, camera-relative and absolute.
        float3 vBehindWs = Depth::GetWorldPosition( i.vPositionSs.xy );
        float3 vBehindRel = vBehindWs - g_vCameraPositionWs;
        float3 vPaneWs = i.vPositionWithOffsetWs.xyz + g_vCameraPositionWs;
        float flWater = clamp( distance( i.vPositionWithOffsetWs.xyz, vBehindRel ) - 1.0, 0.0, g_flMaxWater );

        // The water moving: a small shift of the picture, less the further off the pane is.
        float2 vScreen = i.vPositionSs.xy * g_vInvViewportSize;
        float flCamDist = length( i.vPositionWithOffsetWs.xyz );
        float2 vWobble = float2( sin( vPaneWs.x * 0.043 + vPaneWs.z * 0.031 + t * 1.3 ), cos( vPaneWs.y * 0.047 - vPaneWs.z * 0.029 - t * 1.1 ) );
        vWobble *= g_flRefraction * saturate( flWater / 160.0 ) / max( 1.0, flCamDist / 300.0 );
        float2 vUV = ( vScreen + vWobble ) * g_vFrameBufferCopyInvSizeAndUvScale.zw;
        float3 vBehind = g_tFrameBufferCopyTexture.SampleLevel( g_sTrilinearMirror, vUV, 0 ).rgb;

        // Caustics on what's behind, by its depth under the surface.
        float flBehindDown = max( g_flSurfaceZ - vBehindWs.z, 0.0 );
        float2 vCausticP = ( vBehindWs.xy + vBehindWs.z * float2( 0.35, 0.22 ) ) / g_flCausticScale;
        float flCaustic = Caustic( vCausticP, t * 0.45 ) * 0.6 + Caustic( vCausticP * 1.7 + 13.0, t * 0.6 ) * 0.4;
        flCaustic *= g_flCaustics * exp( -flBehindDown / g_flDeepRange );
        vBehind *= 1.0 + flCaustic * 1.6;

        // The water's own light along the way: lighter near the surface, with shafts through it.
        float3 vShaft = 0;
        [unroll]
        for ( int k = 0; k < 8; k++ )
        {
            float f = ( k + 0.5 ) / 8.0;
            vShaft += Shaft( lerp( vPaneWs, vBehindWs, f ), t );
        }
        vShaft /= 8.0;
        float flPaneDown = max( g_flSurfaceZ - ( vPaneWs.z + vBehindWs.z ) * 0.5, 0.0 );
        // Lit water fades slowly at first, then faster: the top of a show tank is bright all the way across.
        float3 vMedium = lerp( g_vWaterScatter, g_vWaterDeep, pow( saturate( flPaneDown / g_flDeepRange ), 1.4 ) );
        vMedium += g_vWaterScatter * vShaft * g_flShafts * 3.0;

        float3 vTransmit = exp( -( g_vWaterAbsorb + g_flTurbidity ) * flWater );
        float3 vColour = vBehind * vTransmit + vMedium * ( 1.0 - vTransmit );

        // Thick acrylic goes green-blue edge on.
        vColour *= lerp( 1.0.xxx, g_vGlassEdge, pow( 1.0 - flNDotV, 3.0 ) );

        m.Normal = vNormal;
        m.Metalness = 0;
        m.Roughness = g_flGlassRoughness;
        m.Albedo = 0;
        m.AmbientOcclusion = 1;
        m.Emission = vColour * ( 1.0 - vEnvBRDF );
        m.Opacity = 1;

        float4 output = ShadingModelStandard::Shade( m );
        output.a = 1.0f;
        return output;
    }
}
