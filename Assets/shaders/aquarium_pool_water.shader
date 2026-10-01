// Wasseroberfläche des Streichelbeckens (tools/aquarium/aq_pool.js): klares, türkises Wasser wie im Vorlagebild.
// Das Bild darunter (Sand, Steine, Pflanzen) wird durch die gekräuselte Oberfläche leicht verzogen und je nach Weg
// durchs Wasser türkis eingefärbt: flach über dem Sand fast klar, an der Innenwand und in der Tiefe satter. Dazu kleine
// helle Lichtreflexe auf den Wellen, etwas Himmel im Fresnel und ein heller Saum, wo Steine und Wände aus dem Wasser
// kommen. Die Wellen kommen aus Welt-xy (kein Bild), laufen langsam und kacheln nicht sichtbar.
HEADER
{
	Description = "Streichelbecken: klares Wasser mit Brechung, Wellen, Lichtreflexen und Saum";
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
	PixelInput MainVs( VertexInput i )
	{
		return FinalizeVertex( ProcessVertex( i ) );
	}
}

PS
{
	StaticCombo( S_MODE_DEPTH, 0..1, Sys( ALL ) );

	#define DEPTH_STATE_ALREADY_SET 1
	#define BLEND_MODE_ALREADY_SET 1
	#define S_TRANSLUCENT 1

	#include "common/utils/Material.CommonInputs.hlsl"
	#include "common/pixel.hlsl"
	#include "common/classes/Depth.hlsl"

	RenderState( CullMode, NONE );
	BoolAttribute( bWantsFBCopyTexture, true );

	Texture2D g_tFrameBufferCopyTexture < Attribute( "FrameBufferCopyTexture" ); SrgbRead( false ); >;

	// Maske von oben über das Becken (tools/aquarium/tex/pool.js poolRing): Rot = Nähe zur Wasserlinie eines Felsens
	CreateInputTexture2D( TextureRing, Linear, 8, "", "_ring", "Saum,40/30", Default3( 0.0, 0.0, 0.0 ) );
	Texture2D g_tRing < Channel( RGB, Box( TextureRing ), Linear ); OutputFormat( RGBA8888 ); SrgbRead( false ); >;
	SamplerState RingFiltering < Filter( BILINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;

	// Licht, das je Einheit Weg durchs Wasser verloren geht (Rot am meisten: Sand wird mintgrün, Tiefe türkis)
	float3 g_vAbsorb < Default3( 0.045, 0.005, 0.012 ); UiGroup( "Wasser,10/10" ); >;
	// Streulicht im Wasser (türkises Leuchten der tiefen Stellen), wächst mit dem Weg
	float3 g_vScatter < Default3( 0.08, 0.58, 0.47 ); UiType( Color ); UiGroup( "Wasser,10/20" ); >;
	float g_flScatterScale < Default( 45.0 ); Range( 1.0, 400.0 ); UiGroup( "Wasser,10/30" ); >;
	float g_flScatterAmount < Default( 0.45 ); Range( 0.0, 3.0 ); UiGroup( "Wasser,10/40" ); >;
	float g_flRefraction < Default( 0.004 ); Range( 0.0, 0.05 ); UiGroup( "Wellen,20/10" ); >;
	float g_flWaveScale < Default( 1.0 ); Range( 0.1, 5.0 ); UiGroup( "Wellen,20/20" ); >;
	float g_flWaveSpeed < Default( 1.0 ); Range( 0.0, 5.0 ); UiGroup( "Wellen,20/30" ); >;
	float g_flWaveHeight < Default( 1.0 ); Range( 0.0, 4.0 ); UiGroup( "Wellen,20/40" ); >;
	float g_flGlints < Default( 1.0 ); Range( 0.0, 4.0 ); UiGroup( "Licht,30/10" ); >;
	float3 g_vSkyColor < Default3( 0.78, 0.88, 0.9 ); UiType( Color ); UiGroup( "Licht,30/20" ); >;
	float g_flReflection < Default( 0.25 ); Range( 0.0, 2.0 ); UiGroup( "Licht,30/30" ); >;
	float g_flEdge < Default( 0.45 ); Range( 0.0, 2.0 ); UiGroup( "Saum,40/10" ); >;
	float g_flEdgeWidth < Default( 3.0 ); Range( 0.1, 10.0 ); UiGroup( "Saum,40/20" ); >;
	float g_flBrightness < Default( 1.0 ); Range( 0.0, 3.0 ); UiGroup( "Licht,30/40" ); >;
	// Welt x0, y0 und Kantenlänge der Ringmaske; Stärke des Glasrings um die Felsen
	float3 g_vRingRect < Default3( 0.0, 0.0, 1.0 ); UiGroup( "Saum,40/40" ); >;
	float g_flRing < Default( 0.6 ); Range( 0.0, 2.0 ); UiGroup( "Saum,40/50" ); >;

	float Hash21( float2 p )
	{
		p = frac( p * float2( 123.34, 456.21 ) );
		p += dot( p, p + 45.32 );
		return frac( p.x * p.y );
	}

	float Noise( float2 p )
	{
		float2 i = floor( p ), f = frac( p );
		float2 u = f * f * ( 3.0 - 2.0 * f );
		return lerp( lerp( Hash21( i ), Hash21( i + float2( 1, 0 ) ), u.x ), lerp( Hash21( i + float2( 0, 1 ) ), Hash21( i + float2( 1, 1 ) ), u.x ), u.y );
	}

	// Wellenhöhe aus einigen schrägen Wellenzügen und etwas Rauschen (in Welt-Einheiten)
	float Height( float2 p, float t )
	{
		float h = 0.0;
		h += 0.55 * sin( dot( p, float2( 0.21, 0.13 ) ) + t * 1.10 );
		h += 0.45 * sin( dot( p, float2( -0.17, 0.26 ) ) + t * 1.37 + 1.3 );
		h += 0.30 * sin( dot( p, float2( 0.37, -0.29 ) ) + t * 1.83 + 4.1 );
		h += 0.22 * sin( dot( p, float2( -0.46, -0.41 ) ) + t * 2.31 + 2.2 );
		h += 0.9 * ( Noise( p * 0.35 + float2( t * 0.35, t * 0.21 ) ) + Noise( p * 0.63 - float2( t * 0.27, -t * 0.33 ) ) - 1.0 );
		return h;
	}

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		#if S_MODE_DEPTH
			return 1;
		#endif

		float3 wp = i.vPositionWithOffsetWs.xyz + g_vHighPrecisionLightingOffsetWs.xyz;
		float t = g_flTime * g_flWaveSpeed;
		float2 p = wp.xy * g_flWaveScale;
		const float e = 0.35;
		float h0 = Height( p, t );
		float hx = Height( p + float2( e, 0 ), t ), hy = Height( p + float2( 0, e ), t );
		float2 grad = float2( hx - h0, hy - h0 ) / e * 0.22 * g_flWaveHeight;
		float3 n = normalize( float3( -grad, 1.0 ) );

		float3 viewRay = normalize( i.vPositionWithOffsetWs.xyz );
		float ndv = saturate( dot( n, -viewRay ) );

		// Was liegt hinter der Oberfläche und wie weit?
		float2 ssUv = i.vPositionSs.xy * g_vInvViewportSize.xy;
		float3 surfWs = i.vPositionWithOffsetWs.xyz + g_vCameraPositionWs;
		float3 sceneWs = Depth::GetWorldPosition( i.vPositionSs.xy );
		float dist = distance( surfWs, sceneWs );
		// wie tief unter dem Spiegel das liegt, was man hier sieht (für die Wasserlinie an Steinen und Wänden)
		float depthZ = max( 0.0, surfWs.z - sceneWs.z );

		// Brechung: je tiefer, desto mehr Versatz (dicht an Steinen fast keiner, sonst reißen die Kanten)
		float2 offs = n.xy * g_flRefraction * saturate( dist / 6.0 );
		float2 uvR = ( ssUv + offs ) * g_vFrameBufferCopyInvSizeAndUvScale.zw;
		// nie Dinge vor dem Wasser ins Wasser holen: dort, wo der Versatz landet, muss es auch hinter der Oberfläche sein
		float distR = distance( surfWs, Depth::GetWorldPosition( i.vPositionSs.xy + offs / g_vInvViewportSize.xy ) );
		float3 below = g_tFrameBufferCopyTexture.SampleLevel( g_sTrilinearMirror, uvR, 0 ).rgb;
		if ( distR < dist * 0.6 )
		{
			below = g_tFrameBufferCopyTexture.SampleLevel( g_sTrilinearMirror, ssUv * g_vFrameBufferCopyInvSizeAndUvScale.zw, 0 ).rgb;
			distR = dist;
		}

		// Weg durchs Wasser: Rot geht zuerst verloren, dazu türkises Streulicht (heller, wo es darunter hell ist)
		float3 trans = exp( -g_vAbsorb * distR );
		float lum = dot( below, float3( 0.3, 0.55, 0.15 ) );
		// warme, bunte Dinge (Seesterne, Muscheln, Koralle) bleiben kräftig: dort weniger Streulicht als über Sand und
		// den türkisen Fliesen
		float sat = saturate( ( below.r - max( below.g, below.b ) ) / max( below.r, 0.001 ) );
		float3 water = below * trans + g_vScatter * ( 1.0 - exp( -distR / g_flScatterScale ) ) * g_flScatterAmount * ( 0.3 + 0.7 * saturate( lum * 1.6 ) ) * ( 1.0 - 0.75 * smoothstep( 0.15, 0.45, sat ) );
		water *= g_flBrightness;

		// Himmel im Fresnel und helle Lichtreflexe auf den Wellenkämmen
		float fres = 0.02 + 0.98 * pow( 1.0 - ndv, 5.0 );
		float3 refl = g_vSkyColor * fres * g_flReflection;
		// Glitzern: wo die Welle gerade in eine bestimmte Richtung kippt (unabhängig vom Blickwinkel, wandert mit),
		// dazu feine Funken auf den Kämmen
		float3 r = reflect( viewRay, n );
		float3 r0 = reflect( viewRay, normalize( float3( 0.22, -0.12, 1.0 ) ) );
		float glint = pow( saturate( dot( r, r0 ) ), 900.0 ) * 2.5;
		float crest = saturate( ( h0 - 0.4 ) * 0.9 );
		float spark = Noise( p * 2.7 + float2( t * 0.9, -t * 0.4 ) ) * Noise( p * 3.9 - float2( t * 0.5, t * 0.8 ) );
		glint += smoothstep( 0.7, 0.9, spark ) * 0.9 * ( 0.3 + crest );
		glint *= 0.6 + crest;

		// Wasserlinie, wo Steine, Wände und Pflanzen die Oberfläche durchstoßen: ein schmaler heller Glasring (die
		// Wellen heben und senken ihn etwas) und darunter ein breiterer, leicht aufgehellter Saum
		float wob = ( Noise( p * 1.3 + float2( t * 0.5, -t * 0.4 ) ) - 0.5 ) * 0.35;
		float zz = max( 0.0, depthZ + wob );
		float wline = 1.0 - smoothstep( 0.0, g_flEdgeWidth * 0.22, zz );
		float wband = 1.0 - smoothstep( 0.0, g_flEdgeWidth, zz );
		float3 col = water * ( 1.0 - fres * g_flReflection ) + refl + glint * g_flGlints;
		col = lerp( col, col * 0.75 + float3( 0.2, 0.3, 0.3 ), wband * g_flEdge * 0.5 );
		col = lerp( col, float3( 0.82, 0.96, 0.95 ), wline * g_flEdge );

		// Glasring um die Felsen (wie im Bild): Abstand zur Wasserlinie aus der Maske (5 Einheiten Reichweite), von den
		// Wellen etwas verschoben; direkt am Fels eine helle Linie, außen ein klarer, heller Saum mit dunklerem Rand
		float rm = g_tRing.Sample( RingFiltering, ( wp.xy - g_vRingRect.xy ) / g_vRingRect.z ).r;
		float rd = ( 1.0 - rm ) * 5.0 + ( Noise( p * 0.9 + float2( -t * 0.45, t * 0.3 ) ) - 0.5 ) * 0.7 + h0 * 0.12;
		float ringLine = 1.0 - smoothstep( 0.05, 0.45, rd );
		float ringHalo = 1.0 - smoothstep( 0.4, 2.3, rd );
		float ringDark = smoothstep( 1.6, 2.3, rd ) * ( 1.0 - smoothstep( 2.3, 3.2, rd ) );
		col = lerp( col, col * 0.85 + float3( 0.16, 0.26, 0.26 ), ringHalo * g_flRing * 0.55 );
		col *= 1.0 - 0.06 * ringDark * g_flRing;
		col = lerp( col, float3( 0.86, 0.98, 0.97 ), ringLine * g_flRing );

		Material m = Material::Init( i );
		m.Normal = n;
		m.Albedo = 0.02;
		m.Metalness = 1.0;
		m.Roughness = 0.08;
		m.Emission = col;
		if ( ToolsVis::WantsToolsVis() )
		{
			m.Albedo = m.Emission;
			m.Emission = 0;
		}
		float4 output = ShadingModelStandard::Shade( m );
		output.a = 1.0;
		return output;
	}
}
