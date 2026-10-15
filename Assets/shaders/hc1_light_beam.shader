HEADER
{
    Description = "A lamp's beam through hazy night air (Riverside's searchlight): an additive cone, brightest near the lamp and fading along its length, soft at its silhouette's edges where the eye looks through less of it, and where it meets the ground";
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
    BoolAttribute( translucent, true );
    RenderState( DepthWriteEnable, false );
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, ONE );
    RenderState( DstBlend, ONE );
    RenderState( CullMode, NONE );

    float3 g_vBeamColour < UiType( Color ); Default3( 0.8, 0.85, 1.0 ); UiGroup( "Beam,10/10" ); >;
    float g_flBeamIntensity < Default( 1.0 ); Range( 0.0, 20.0 ); UiGroup( "Beam,10/20" ); >;
    // How far along the cone (its texture's v, 0 at the lamp) the beam has faded out.
    float g_flBeamReach < Default( 1.0 ); Range( 0.1, 1.0 ); UiGroup( "Beam,10/30" ); >;
    // Units over which the beam fades where it meets something behind it (the ground it lights).
    float g_flSoftDepth < Default( 40.0 ); Range( 0.0, 400.0 ); UiGroup( "Beam,10/40" ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float along = saturate( i.vTextureCoords.y / max( g_flBeamReach, 0.01 ) );
        float3 N = normalize( i.vNormalWs );
        float3 V = normalize( -i.vPositionWithOffsetWs );
        // Through the middle of the cone the eye looks through more lit air than at its edges.
        float through = pow( saturate( abs( dot( N, V ) ) ), 1.4 );
        // Bright off the lens, then thinning out as the light spreads.
        float fade = pow( 1.0 - along, 1.8 ) * ( 0.35 + 0.65 * saturate( along * 10.0 ) ) + 0.6 * exp( -along * 40.0 );

        // Soft where the cone passes into the ground or a wall.
        float sceneDistance = length( Depth::GetWorldPosition( i.vPositionSs.xy ) - g_vCameraPositionWs );
        float beamDistance = length( i.vPositionWithOffsetWs );
        float soft = g_flSoftDepth > 0.0 ? saturate( ( sceneDistance - beamDistance ) / g_flSoftDepth ) : 1.0;

        float3 colour = g_vBeamColour * g_flBeamIntensity * through * fade * soft;
        return float4( colour, 1.0 );
    }
}
