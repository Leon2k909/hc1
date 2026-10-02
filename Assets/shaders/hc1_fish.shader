//=========================================================================================================================
// HC1 fish: swimming bodies for the aquarium tanks' animals (Code/Maps/TankFauna.cs, models from Tools/reefhall_fauna.py).
//
// The models face +X with their middle at the origin, Y to the left and Z up. A fish swims with a wave running from its
// head to its tail, small at the head and growing towards the tail fin (carangiform swimming, as sharks, tangs and chromis
// do). A ray instead flaps its wings: the wingtips rise and fall, the wave running back from the leading edge, and the
// body stays still. g_flRay picks between the two.
//
// Each animal is a SceneObject of its own, scaled 0.85-1.15 by TankFauna, and the scale sets its phase, so neighbours in
// a school don't beat in step.
//=========================================================================================================================
HEADER
{
	Description = "HC1 fish: a swimming wave along the body, or a ray's wingbeat";
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

//=========================================================================================================================

VS
{
	#include "common/vertex.hlsl"

	// The body's length, nose to tail, in model units (the nose at +Length / 2)
	float g_flBodyLength < Default( 72.0 ); Range( 1.0, 500.0 ); UiGroup( "Swim,10/Body" ); >;
	// The tail's sideways swing, as a share of the length
	float g_flSwingAmount < Default( 0.08 ); Range( 0.0, 0.5 ); UiGroup( "Swim,10/Body" ); >;
	// Tail beats a second
	float g_flBeatRate < Default( 1.0 ); Range( 0.0, 10.0 ); UiGroup( "Swim,10/Body" ); >;
	// Body lengths per wave: under 1, more than one bend shows along the body (an eel's), over 1 it's stiffer
	float g_flWaveLength < Default( 1.1 ); Range( 0.2, 5.0 ); UiGroup( "Swim,10/Body" ); >;

	// 1: a ray. The wingspan, and the wingtips' rise and fall as a share of it
	float g_flRay < Default( 0.0 ); Range( 0.0, 1.0 ); UiGroup( "Swim,20/Ray" ); >;
	float g_flSpan < Default( 140.0 ); Range( 1.0, 1000.0 ); UiGroup( "Swim,20/Ray" ); >;
	float g_flFlapAmount < Default( 0.12 ); Range( 0.0, 0.5 ); UiGroup( "Swim,20/Ray" ); >;

	PixelInput MainVs( VertexInput i )
	{
		PixelInput o = ProcessVertex( i );

		float3x4 matObjectToWorld = GetTransformMatrix( i.nInstanceTransformID );
		float flScale = length( float3( matObjectToWorld[0][0], matObjectToWorld[1][0], matObjectToWorld[2][0] ) );
		float flPhase = flScale * 2513.27;
		float flTime = g_flTime * g_flBeatRate * 6.2831853 + flPhase;

		float3 p = i.vPositionOs.xyz;
		float L = g_flBodyLength;

		// Fish: 0 at the nose, 1 at the tail fin's tip. The swing grows with the square of that, from a little at the head
		float s01 = saturate( ( 0.5 * L - p.x ) / L );
		float flEnvelope = 0.18 + 0.82 * s01 * s01;
		float flWave = sin( flTime - s01 * 6.2831853 / g_flWaveLength );
		float3 vFish = p;
		vFish.y += g_flSwingAmount * L * flEnvelope * flWave;
		// The body bends rather than shears: points swinging out come forward a touch
		vFish.x -= g_flSwingAmount * L * flEnvelope * 0.15 * abs( flWave ) * s01;

		// Ray: the wings bend up and down from the body, more towards the tips, the wave running back from the front
		float flOut = saturate( abs( p.y ) / ( 0.5 * g_flSpan ) );
		float flChord = saturate( ( 0.5 * L - p.x ) / L );
		float3 vRay = p;
		vRay.z += g_flFlapAmount * g_flSpan * pow( flOut, 1.5 ) * sin( flTime - flChord * 1.6 );
		// Wingtips come in a little as they rise or fall, so the wing doesn't stretch
		vRay.y *= 1.0 - 0.06 * pow( flOut, 2.0 ) * abs( sin( flTime - flChord * 1.6 ) );

		float3 vPositionOs = lerp( vFish, vRay, g_flRay );

		o.vPositionWs = mul( matObjectToWorld, float4( vPositionOs, 1.0 ) );
		o.vPositionPs.xyzw = Position3WsToPs( o.vPositionWs.xyz );

		return FinalizeVertex( o );
	}
}

//=========================================================================================================================

PS
{
	#include "common/utils/Material.CommonInputs.hlsl"
	#include "common/pixel.hlsl"

	#if ( S_MODE_DEPTH == 0 )
		RenderState( DepthFunc, EQUAL );
		RenderState( DepthWriteEnable, false );
	#endif

	// Wet skin: a little sheen, never a mirror
	float g_flMinRoughness < Default( 0.35 ); Range( 0.0, 1.0 ); UiGroup( "Fish" ); >;

	#if ( S_MODE_DEPTH == 0 )
		[earlydepthstencil]
	#endif
	float4 MainPs( PixelInput i ) : SV_Target0
	{
		Material m = Material::From( i );
		m.Roughness = max( m.Roughness, g_flMinRoughness );
		return ShadingModelStandard::Shade( i, m );
	}
}
