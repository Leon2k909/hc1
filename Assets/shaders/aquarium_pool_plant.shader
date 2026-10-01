// Tang und Wasserpflanzen im Streichelbecken (tools/aquarium/aq_pool.js): Blätter mit Alpha aus dem Atlas, die sich
// in der Strömung wiegen. Der Ausschlag wächst mit der Höhe über dem Beckengrund – der Fuß bleibt stehen, die Spitzen schwingen; jede Stelle im Becken mit eigener Phase. Unter Wasser wandert das Lichtnetz
// auch über die Blätter. Der Grund ist eine flache Mulde: an der Wand g_flFloorZ, in der Mitte (innerhalb
// g_flRiseR0 um g_flPoolX/Y) um g_flFloorRise höher, dazwischen weicher Übergang bis g_flRiseR1 (wie sandZ in aq_pool_shape.js).
HEADER
{
	Description = "Streichelbecken: Wasserpflanzen wiegen sich in der Strömung";
	Version = 1;
}

FEATURES
{
	#include "common/features.hlsl"
}

MODES
{
	Forward();
	Depth( S_MODE_DEPTH );
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
	#if ( PROGRAM == VFX_PROGRAM_PS )
		bool bIsFrontface : SV_IsFrontFace;
	#endif
};

VS
{
	#include "common/vertex.hlsl"

	float g_flFloorZ < Default( 5.0 ); Range( -1000.0, 1000.0 ); UiGroup( "Stroemung,10/10" ); >;
	float g_flFloorRise < Default( 0.0 ); Range( 0.0, 100.0 ); UiGroup( "Grund,20/10" ); >;
	float g_flRiseR0 < Default( 52.0 ); Range( 0.0, 1000.0 ); UiGroup( "Grund,20/20" ); >;
	float g_flRiseR1 < Default( 80.0 ); Range( 0.0, 1000.0 ); UiGroup( "Grund,20/30" ); >;
	float g_flPoolX < Default( 0.0 ); Range( -10000.0, 10000.0 ); UiGroup( "Grund,20/40" ); >;
	float g_flPoolY < Default( 0.0 ); Range( -10000.0, 10000.0 ); UiGroup( "Grund,20/50" ); >;
	float g_flSwayHeight < Default( 26.0 ); Range( 1.0, 200.0 ); UiGroup( "Stroemung,10/20" ); >;
	float g_flSwayAmount < Default( 2.2 ); Range( 0.0, 20.0 ); UiGroup( "Stroemung,10/30" ); >;
	float g_flSwaySpeed < Default( 0.9 ); Range( 0.0, 5.0 ); UiGroup( "Stroemung,10/40" ); >;

	PixelInput MainVs( VertexInput i )
	{
		PixelInput o = ProcessVertex( i );
		float3 wp = o.vPositionWs.xyz;
		float floorZ = g_flFloorZ + g_flFloorRise * ( 1.0 - smoothstep( g_flRiseR0, g_flRiseR1, length( wp.xy - float2( g_flPoolX, g_flPoolY ) ) ) );
		float h = saturate( ( wp.z - floorZ ) / g_flSwayHeight );
		float w = h * h * ( 1.6 - 0.6 * h );
		// Phase nach Ort: benachbarte Blätter eines Büschels fast gleich, Büschel untereinander verschieden
		float ph = dot( wp.xy, float2( 0.071, 0.113 ) ) + sin( wp.x * 0.05 + wp.y * 0.031 ) * 2.0;
		float t = g_flTime * g_flSwaySpeed;
		float2 sway = float2( sin( t + ph ) + 0.35 * sin( t * 2.3 + ph * 1.7 + wp.z * 0.15 ),
			0.6 * cos( t * 0.8 + ph * 1.3 ) + 0.25 * sin( t * 1.9 - ph + wp.z * 0.2 ) );
		wp.xy += sway * w * g_flSwayAmount;
		// Spitzen sinken beim Ausschlag etwas ab, damit die Blätter nicht länger werden
		wp.z -= dot( sway, sway ) * w * g_flSwayAmount * 0.08;
		o.vPositionWs.xyz = wp;
		o.vPositionPs.xyzw = Position3WsToPs( wp );
		return FinalizeVertex( o );
	}
}

PS
{
	#include "common/utils/Material.CommonInputs.hlsl"
	#include "common/pixel.hlsl"

	RenderState( CullMode, NONE );

	float g_flAlphaTestReference < Default( 0.5 ); Range( 0.0, 1.0 ); UiGroup( "Material,10/80" ); >;
	float g_flRoughnessScaleFactor < Default( 1.0 ); Range( 0.0, 2.0 ); UiGroup( "Material,10/35" ); >;
	float g_flWaterZ < Default( 25.0 ); Range( -1000.0, 1000.0 ); UiGroup( "Wasser,10/10" ); >;
	float g_flCaustics < Default( 0.35 ); Range( 0.0, 3.0 ); UiGroup( "Wasser,10/20" ); >;
	float g_flTranslucency < Default( 0.35 ); Range( 0.0, 1.0 ); UiGroup( "Material,10/90" ); >;

	float Caustic( float2 p, float time )
	{
		const float TAU = 6.28318;
		float2 q = frac( p ) * TAU - 250.0;
		float2 k = q;
		float c = 1.0;
		for ( int n = 0; n < 4; n++ )
		{
			float t = time * ( 1.0 - 3.5 / float( n + 1 ) );
			k = q + float2( cos( t - k.x ) + sin( t + k.y ), sin( t - k.y ) + cos( t + k.x ) );
			c += 1.0 / length( float2( q.x / ( sin( k.x + t ) / 0.005 ), q.y / ( cos( k.y + t ) / 0.005 ) ) );
		}
		c = 1.17 - pow( c / 4.0, 1.4 );
		return pow( abs( c ), 8.0 );
	}

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		Material m = Material::From( i );
		clip( m.Opacity - g_flAlphaTestReference );
		m.Opacity = 1.0;
		m.Metalness = 0.0;
		m.Roughness = saturate( m.Roughness * g_flRoughnessScaleFactor );
		if ( !i.bIsFrontface ) m.Normal = -m.Normal;

		float3 wp = i.vPositionWithOffsetWs.xyz + g_vHighPrecisionLightingOffsetWs.xyz;
		// durchscheinende Blätter: etwas Eigenleuchten in der Blattfarbe, damit die Rückseiten nicht schwarz werden
		m.Emission += m.Albedo * g_flTranslucency * 0.35;
		float under = saturate( ( g_flWaterZ - wp.z ) / 1.2 );
		if ( under > 0.0 )
		{
			float c = Caustic( wp.xy / 36.0, g_flTime * 0.45 + 20.0 );
			m.Emission += m.Albedo * c * g_flCaustics * under;
		}
		return ShadingModelStandard::Shade( m );
	}
}
