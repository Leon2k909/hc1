// Grund, Innenwand, Felsen und Kleinzeug im Streichelbecken (tools/aquarium/aq_pool.js): ganz normal beleuchtete
// Oberfläche mit Farbe, Normal-Map und Rauheit, darunter wandert unter Wasser ein helles Lichtnetz (Kaustik), wie es
// die gekräuselte Oberfläche auf Sand und Steine wirft. Über dem Wasserspiegel (g_flWaterZ, Welt-z) bleibt es aus.
HEADER
{
	Description = "Streichelbecken: Grund und Steine mit wanderndem Lichtnetz unter Wasser";
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
};

VS
{
	#include "common/vertex.hlsl"
	PixelInput MainVs( VertexInput i )
	{
		return FinalizeVertex( ProcessVertex( i ) );
	}
}

PS
{
	#include "common/utils/Material.CommonInputs.hlsl"
	#include "common/pixel.hlsl"

	RenderState( CullMode, F_RENDER_BACKFACES ? NONE : DEFAULT );

	float g_flWaterZ < Default( 25.0 ); Range( -1000.0, 1000.0 ); UiGroup( "Wasser,10/10" ); >;
	float g_flCaustics < Default( 0.6 ); Range( 0.0, 3.0 ); UiGroup( "Wasser,10/20" ); >;
	float g_flCausticScale < Default( 36.0 ); Range( 4.0, 200.0 ); UiGroup( "Wasser,10/30" ); >;
	float g_flCausticSpeed < Default( 0.45 ); Range( 0.0, 3.0 ); UiGroup( "Wasser,10/40" ); >;
	float3 g_vCausticTint < Default3( 1.0, 0.98, 0.9 ); UiType( Color ); UiGroup( "Wasser,10/50" ); >;
	// Tönung unter Wasser: zwischen den Lichtlinien (Sand wird dort türkis, im Licht bleibt er warm) und für nasse
	// Flächen überhaupt (Felsen unter dem Wasserspiegel blaugrau, trocken oben hell)
	float3 g_vGapTint < Default3( 1.0, 1.0, 1.0 ); UiGroup( "Wasser,10/60" ); >;
	float3 g_vWetTint < Default3( 1.0, 1.0, 1.0 ); UiGroup( "Wasser,10/70" ); >;
	// breite, weiche Lichtflecken (Sonne durch die großen Wellen), warm; dort bleibt der Sand hell statt türkis
	float g_flBroad < Default( 0.0 ); Range( 0.0, 3.0 ); UiGroup( "Wasser,10/80" ); >;
	float g_flRoughnessScaleFactor < Default( 1.0 ); Range( 0.0, 2.0 ); UiGroup( "Material,10/35" ); >;

	// Kachelbares Lichtnetz (wie im Endbecken), p in Kacheln.
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
		m.Metalness = 0.0;
		m.Roughness = saturate( m.Roughness * g_flRoughnessScaleFactor );

		float3 wp = i.vPositionWithOffsetWs.xyz + g_vHighPrecisionLightingOffsetWs.xyz;
		float under = saturate( ( g_flWaterZ - wp.z ) / 1.2 );
		m.Albedo *= lerp( float3( 1.0, 1.0, 1.0 ), g_vWetTint, saturate( ( g_flWaterZ + 0.6 - wp.z ) / 1.0 ) );
		if ( under > 0.0 )
		{
			// zwei gegeneinander laufende Netze, das hellere zählt: wirkt weniger regelmäßig
			float t = g_flTime * g_flCausticSpeed + 20.0;
			float2 p = wp.xy / g_flCausticScale;
			float c1 = Caustic( p, t );
			float c2 = Caustic( p * 1.37 + float2( 0.31, 0.57 ), t * 0.83 + 7.0 );
			float c = saturate( max( c1, c2 * 0.85 ) );
			c = saturate( pow( c, 1.4 ) * 1.3 );   // schmalere, hellere Linien
			// nach oben (schräge Wände, Felsflanken) schwächer, zum Grund hin voll
			float up = saturate( i.vNormalWs.z * 0.6 + 0.55 );
			// helle Linien, dazwischen etwas dunkler (wie Sonnenlicht durch Wellen)
			float k = g_flCaustics * under * up;
			float2 bw = wp.xy * 0.055;
			float wv = sin( bw.x * 1.3 + bw.y * 0.6 + t * 0.3 + 1.7 * sin( bw.y * 0.9 - t * 0.21 ) )
				* sin( -bw.x * 0.5 + bw.y * 1.1 - t * 0.24 + 1.3 * sin( bw.x * 0.8 + t * 0.17 ) );
			float broad = smoothstep( 0.0, 0.75, wv ) * g_flBroad * under * up;
			float gap = saturate( k ) * ( 1.0 - c ) * ( 1.0 - 0.6 * saturate( broad ) );
			m.Albedo *= lerp( float3( 1.0, 1.0, 1.0 ), g_vGapTint, gap ) * ( 1.0 - 0.26 * gap );
			m.Emission += m.Albedo * g_vCausticTint * ( c * k + broad );
		}
		return ShadingModelStandard::Shade( m );
	}
}
