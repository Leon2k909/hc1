//=========================================================================================================================
// HC1 fish: swimming bodies for the aquarium tanks' animals (Code/Maps/TankFauna.cs, models from Tools/reefhall_fauna.py).
//
// The models face +X, Y to the left and Z up, the nose at g_flNoseX. A fish swims with a wave running from its head to its
// tail, small at the head and growing towards the tail fin (carangiform swimming). Its pectoral fins (the texture's U
// 0.5-0.58 strip, see the fauna script) scull: they swing back and forth from their roots, the wave running out to their
// tips. A ray instead flaps its wings, the wave running back from the leading edge. g_flRay picks between the two.
//
// TankFauna drives each animal through its SceneObject's attributes: SwimPhase (the tail's phase, radians, which it
// advances faster when the fish speeds up or turns), SwimAmount (how hard it swims: a hovering fish barely beats its
// tail, a turning one swings it more), and FinPhase / FinAmount for the pectorals (a hovering fish sculls with them).
// With SwimDriven 0 (an animal placed by hand) it swims on the clock, its phase set by its scale.
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

	// The body's length, nose to tail, and where its nose is, in model units
	float g_flBodyLength < Default( 72.0 ); Range( 1.0, 500.0 ); UiGroup( "Swim,10/Body" ); >;
	float g_flNoseX < Default( 36.0 ); Range( -500.0, 500.0 ); UiGroup( "Swim,10/Body" ); >;
	// The tail's sideways swing, as a share of the length
	float g_flSwingAmount < Default( 0.08 ); Range( 0.0, 0.5 ); UiGroup( "Swim,10/Body" ); >;
	// Tail beats a second, when it isn't driven
	float g_flBeatRate < Default( 1.0 ); Range( 0.0, 10.0 ); UiGroup( "Swim,10/Body" ); >;
	// Body lengths per wave: under 1, more than one bend shows along the body (an eel's), over 1 it's stiffer
	float g_flWaveLength < Default( 1.1 ); Range( 0.2, 5.0 ); UiGroup( "Swim,10/Body" ); >;

	// The pectorals: their length, how far they swing (a share of it) and beats a second when not driven
	float g_flFinReach < Default( 0.0 ); Range( 0.0, 100.0 ); UiGroup( "Swim,15/Fins" ); >;
	float g_flFinSwing < Default( 0.0 ); Range( 0.0, 1.0 ); UiGroup( "Swim,15/Fins" ); >;
	float g_flFinRate < Default( 0.0 ); Range( 0.0, 10.0 ); UiGroup( "Swim,15/Fins" ); >;

	// 1: a ray. The wingspan, and the wingtips' rise and fall as a share of it
	float g_flRay < Default( 0.0 ); Range( 0.0, 1.0 ); UiGroup( "Swim,20/Ray" ); >;
	float g_flSpan < Default( 140.0 ); Range( 1.0, 1000.0 ); UiGroup( "Swim,20/Ray" ); >;
	float g_flFlapAmount < Default( 0.12 ); Range( 0.0, 0.5 ); UiGroup( "Swim,20/Ray" ); >;

	// Set per animal by TankFauna
	float g_flSwimDriven < Attribute( "SwimDriven" ); Default( 0.0 ); >;
	float g_flSwimPhase < Attribute( "SwimPhase" ); Default( 0.0 ); >;
	float g_flSwimAmount < Attribute( "SwimAmount" ); Default( 1.0 ); >;
	float g_flFinPhase < Attribute( "FinPhase" ); Default( 0.0 ); >;
	float g_flFinAmount < Attribute( "FinAmount" ); Default( 1.0 ); >;

	PixelInput MainVs( VertexInput i )
	{
		PixelInput o = ProcessVertex( i );

		float3x4 matObjectToWorld = GetTransformMatrix( i.nInstanceTransformID );
		float flScale = length( float3( matObjectToWorld[0][0], matObjectToWorld[1][0], matObjectToWorld[2][0] ) );
		float flOwnPhase = flScale * 2513.27;
		float flDriven = step( 0.5, g_flSwimDriven );
		float flTime = lerp( g_flTime * g_flBeatRate * 6.2831853 + flOwnPhase, g_flSwimPhase, flDriven );
		float flAmount = lerp( 1.0, g_flSwimAmount, flDriven );
		float flFinTime = lerp( g_flTime * g_flFinRate * 6.2831853 + flOwnPhase * 1.37, g_flFinPhase, flDriven );
		float flFinAmount = lerp( 1.0, g_flFinAmount, flDriven );

		float3 p = i.vPositionOs.xyz;
		float L = g_flBodyLength;

		// Fish: 0 at the nose, 1 at the tail fin's tip. The swing grows with the square of that, from a little at the head
		float s01 = saturate( ( g_flNoseX - p.x ) / L );
		float flEnvelope = 0.18 + 0.82 * s01 * s01;
		float flWave = sin( flTime - s01 * 6.2831853 / g_flWaveLength );
		float flSwing = g_flSwingAmount * L * flAmount * flEnvelope;
		float3 vFish = p;
		vFish.y += flSwing * flWave;
		// The body bends rather than shears: points swinging out come forward a touch
		vFish.x -= flSwing * 0.15 * abs( flWave ) * s01;

		// The pectorals scull from their roots, more towards their tips, opening a little on each stroke
		float2 vUv = i.vTexCoord.xy;
		float flPectoral = step( 0.5, vUv.x ) * step( vUv.x, 0.58 );
		float flSpan = saturate( ( vUv.x - 0.5 ) / 0.08 );
		float flStroke = g_flFinSwing * flFinAmount * flSpan * g_flFinReach * flPectoral;
		vFish.x += flStroke * sin( flFinTime - flSpan * 1.5 );
		vFish.y += sign( p.y ) * flStroke * 0.4 * ( 0.5 + 0.5 * cos( flFinTime - flSpan * 1.5 ) );

		// Ray: the wings bend up and down from the body, more towards the tips, the wave running back from the front
		float flOut = saturate( abs( p.y ) / ( 0.5 * g_flSpan ) );
		float flChord = saturate( ( g_flNoseX - p.x ) / L );
		float flFlap = sin( flTime - flChord * 1.6 );
		float3 vRay = p;
		vRay.z += g_flFlapAmount * flAmount * g_flSpan * pow( flOut, 1.5 ) * flFlap;
		// Wingtips come in a little as they rise or fall, so the wing doesn't stretch
		vRay.y *= 1.0 - 0.06 * pow( flOut, 2.0 ) * abs( flFlap );

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
