// Lebendiges Riffbeckenbild reef_scene_color.png (Anker, Kisten, Amphore; erzeugt von tools/aquarium/tex/reef_scene.js).
// reef_scene_motion.png sagt, was sich wo bewegt (u rechts, v unten):
//   R  Ausschlag der Pflanzen (0 am Fuß, 1 an der Spitze)   G  Phase der Pflanzengruppe
//   B  feste Dinge (Felsen, Anker, Kisten, Korallen)         A  oben freies Wasser, unten heller Sand
// reef_scene_bubbles.png trägt die Blasenketten (R Weg, G seitlicher Abstand, B Fortschritt, A Größe und Nummer).
// Tang und Seegras wiegen sich, Luftblasen steigen in Ketten auf und pendeln, die Oberfläche kräuselt sich, die
// Lichtstrahlen flackern, Schwebteilchen treiben und über den Sand wandert ein Lichtnetz.
// Das Bild ist über die Beckenöffnung hinaus gespiegelt (MIRROR), damit schräge Blicke keine Kante sehen.
HEADER
{
	Description = "Riffbecken: Pflanzen in der Strömung, aufsteigende Luftblasen, bewegtes Wasser und Licht";
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
	#include "common/pixel.hlsl"

	RenderState( CullMode, F_RENDER_BACKFACES ? NONE : DEFAULT );
	BoolAttribute( DoNotCastShadows, true );
	BoolAttribute( SupportsMappingDimensions, true );

	CreateInputTexture2D( TextureColor, Srgb, 8, "", "_color", "Material,10/10", Default3( 1.0, 1.0, 1.0 ) );
	CreateInputTexture2D( TextureMotion, Linear, 8, "", "_motion", "Material,10/15", Default4( 0.0, 0.5, 0.0, 0.0 ) );
	CreateInputTexture2D( TextureBubbles, Linear, 8, "", "_bubbles", "Material,10/16", Default4( 0.0, 0.5, 0.0, 0.0 ) );
	Texture2D g_tScene < Channel( RGB, Box( TextureColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tMotion < Channel( RGBA, Box( TextureMotion ), Linear ); OutputFormat( RGBA8888 ); SrgbRead( false ); >;
	Texture2D g_tBubbles < Channel( RGBA, Box( TextureBubbles ), Linear ); OutputFormat( RGBA8888 ); SrgbRead( false ); >;
	SamplerState SceneFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( MIRROR ); AddressV( MIRROR ); >;
	SamplerState MotionFiltering < Filter( BILINEAR ); AddressU( MIRROR ); AddressV( MIRROR ); >;
	SamplerState BubbleFiltering < Filter( BILINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
	TextureAttribute( LightSim_DiffuseAlbedoTexture, g_tScene );
	TextureAttribute( RepresentativeTexture, g_tScene );
	float g_flSelfIllumBrightness < Default( 0.55 ); Range( 0.0, 4.0 ); UiGroup( "Material,10/20" ); >;
	float g_flAspect < Default( 2.1 ); Range( 0.5, 4.0 ); UiGroup( "Material,10/30" ); >;

	float g_flCurrentStrength < Default( 0.011 ); Range( 0.0, 0.03 ); UiGroup( "Stroemung,10/10" ); >;
	float g_flCurrentSpeed < Default( 0.8 ); Range( 0.0, 2.0 ); UiGroup( "Stroemung,10/20" ); >;
	float g_flSurfaceRipple < Default( 0.003 ); Range( 0.0, 0.01 ); UiGroup( "Stroemung,10/30" ); >;
	float g_flRayFlicker < Default( 0.12 ); Range( 0.0, 0.5 ); UiGroup( "Wasser,20/10" ); >;
	float g_flCaustics < Default( 0.3 ); Range( 0.0, 1.0 ); UiGroup( "Wasser,20/20" ); >;
	float g_flParticles < Default( 0.3 ); Range( 0.0, 1.0 ); UiGroup( "Wasser,20/30" ); >;
	float g_flBubbles < Default( 1.0 ); Range( 0.0, 2.0 ); UiGroup( "Blasen,30/10" ); >;
	float g_flBubbleSpeed < Default( 1.0 ); Range( 0.0, 3.0 ); UiGroup( "Blasen,30/20" ); >;
	float g_flBubbleDensity < Default( 0.85 ); Range( 0.0, 1.0 ); UiGroup( "Blasen,30/30" ); >;

	float Hash( float2 p )
	{
		return frac( sin( dot( p, float2( 127.1, 311.7 ) ) ) * 43758.5453 );
	}

	// Kachelbares Lichtnetz (Wasserkaustik), p in Kacheln.
	float Caustic( float2 p, float time )
	{
		const float TAU = 6.28318;
		float2 q = frac( p ) * TAU - 250.0;
		float2 i = q;
		float c = 1.0;
		for ( int n = 0; n < 4; n++ )
		{
			float t = time * ( 1.0 - 3.5 / float( n + 1 ) );
			i = q + float2( cos( t - i.x ) + sin( t + i.y ), sin( t - i.y ) + cos( t + i.x ) );
			c += 1.0 / length( float2( q.x / ( sin( i.x + t ) / 0.005 ), q.y / ( cos( i.y + t ) / 0.005 ) ) );
		}
		c = 1.17 - pow( c / 4.0, 1.4 );
		return pow( abs( c ), 8.0 );
	}

	// Aufsteigende Schwebteilchen: je Zelle höchstens ein weiches Pünktchen, das leicht pendelt.
	float Particles( float2 uv, float t, float cells, float rise, float seed )
	{
		float2 p = float2( uv.x * 2.0 * cells, uv.y * cells + t * rise );
		float2 cell = floor( p ), f = p - cell;
		float h1 = Hash( cell + seed ), h2 = Hash( cell.yx + seed * 3.0 + 17.0 );
		float on = step( 0.55, Hash( cell + float2( seed - 9.0, 41.0 ) ) );
		float2 c = float2( 0.2 + 0.6 * h1 + 0.12 * sin( t * 0.7 + h2 * 6.28 ), 0.2 + 0.6 * h2 );
		float size = 0.035 + 0.035 * h2;
		return on * smoothstep( size, size * 0.3, length( f - c ) ) * ( 0.6 + 0.4 * sin( t * 1.3 + h1 * 20.0 ) );
	}

	// Eine gemalte Luftblase: dünner heller Rand (oben links und unten kräftiger), milchiger Saum innen am Rand,
	// heller Bogen unten dicht am Rand und ein kleiner Glanzpunkt oben rechts. dp Abstand zur Blasenmitte und r Radius
	// in Bildpixeln (Höhe/1024), aa Breite eines Bildschirmpixels darin.
	// Ergebnis: x Weißanteil, y Deckung der Blase (dort wird das Bild dahinter gebrochen gezeigt).
	float2 Bubble( float2 dp, float r, float aa )
	{
		float d = length( dp );
		float body = saturate( ( r - d ) / aa + 0.5 );
		if ( body <= 0.0 ) return 0.0;
		float2 p = dp / r;
		float e = d / r;
		float w = max( 1.0, r * 0.1 );
		float ring = saturate( 1.0 - abs( d - ( r - w ) ) / max( w, aa ) ) * ( 0.5 + 0.3 * saturate( ( -p.x - p.y ) * 0.8 ) + 0.3 * saturate( p.y ) );
		float edge = smoothstep( 0.6, 1.0, e );
		edge *= edge * ( 0.3 + 0.5 * saturate( ( -p.x - p.y ) * 0.7 ) );
		float crescent = smoothstep( 0.66, 0.92, e ) * smoothstep( 0.3, 0.85, p.y ) * ( 1.0 - smoothstep( 0.97, 1.0, e ) ) * 0.7;
		float spot = smoothstep( 0.2, 0.06, length( ( p - float2( 0.42, -0.5 ) ) * float2( 1.0, 1.1 ) ) );
		// kleine Blasen sind fast nur ein heller Kringel
		float tiny = saturate( 1.0 - ( r - 1.5 ) / 3.0 );
		float white = ( ring * 1.3 + edge * 0.8 + crescent * 1.2 + spot + 0.03 ) * ( 1.0 - tiny ) + tiny * saturate( ring * 1.6 + 0.4 );
		return float2( saturate( white ) * body, body );
	}

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		float2 uv = i.vTextureCoords.xy;
		float t = g_flTime * g_flCurrentSpeed + 40.0;
		float2 uvDx = ddx( uv ), uvDy = ddy( uv );
		float4 mk = g_tMotion.Sample( MotionFiltering, uv );

		// Pflanzen: die Biegung läuft vom Fuß zur Spitze, jede Gruppe mit eigener Phase.
		float ph = mk.g * 6.2832;
		float wave = 0.7 * sin( t + ph - uv.y * 3.0 ) + 0.3 * sin( t * 1.63 + ph * 2.0 + uv.x * 25.0 - uv.y * 5.0 );
		float2 offset = float2( wave, 0.15 * cos( t * 0.9 + ph - uv.y * 3.0 ) ) * mk.r * g_flCurrentStrength;

		// Wasseroberfläche kräuselt sich (nur im freien Wasser)
		float top = 1.0 - smoothstep( 0.08, 0.16, uv.y );
		offset += float2( sin( t * 0.8 + uv.x * 31.0 + uv.y * 40.0 ) + 0.5 * sin( t * 1.3 - uv.x * 55.0 ),
			0.6 * sin( t * 1.1 + uv.x * 41.0 ) ) * top * mk.a * g_flSurfaceRipple;

		// Nie aus festen Dingen lesen: sonst würden Anker oder Kisten in die Pflanzen hineinwachsen.
		offset *= 1.0 - g_tMotion.Sample( MotionFiltering, uv + offset ).b;

		float2 suv = uv + offset;
		i.vTextureCoords.xy = suv;
		float3 color = g_tScene.SampleGrad( SceneFiltering, suv, uvDx, uvDy ).rgb;

		// Lichtstrahlen aus der Sonne über der Bildmitte flackern breit und langsam.
		float2 d = float2( ( uv.x - 0.53 ) * 1.7, uv.y + 0.1 );
		float ang = atan2( d.x, d.y );
		float shafts = sin( ang * 11.0 + t * 0.3 ) * ( 0.6 + 0.4 * sin( ang * 5.0 - t * 0.17 + 1.3 ) );
		float lum = dot( color, float3( 0.3, 0.5, 0.2 ) );
		float ray = saturate( ( lum - 0.4 ) * 2.2 ) * smoothstep( 0.04, 0.12, uv.y ) * ( 1.0 - smoothstep( 0.45, 0.8, uv.y ) );
		float3 lit = color * ( 1.0 + g_flRayFlicker * ray * shafts );

		// Lichtnetz auf dem Sand, perspektivisch zum Horizont hin enger
		float bottom = smoothstep( 0.73, 0.83, uv.y ) * mk.a;
		float depth = 1.0 / max( uv.y - 0.62, 0.02 );
		float caustic = Caustic( float2( ( uv.x - 0.5 ) * depth * 4.2, depth * 1.2 ), t * 0.5 );
		lit += color * caustic * bottom * g_flCaustics;

		// Schwebteilchen im freien Wasser
		float open = mk.a * ( 1.0 - smoothstep( 0.55, 0.7, uv.y ) );
		float specks = Particles( uv, t, 18.0, 0.35, 0.0 ) + 0.6 * Particles( uv, t, 30.0, 0.22, 5.0 );
		lit += float3( 0.7, 0.9, 1.0 ) * specks * open * g_flParticles;

		// Luftblasen: entlang jeder Kette Zellen, die mit den Blasen nach oben wandern. Große und kleine Blasen
		// steigen verschieden schnell und pendeln im Zickzack um die Kette.
		float aa = max( length( float2( uvDx.y, uvDy.y ) ) * 1024.0, 0.35 );
		float4 bm = g_tBubbles.SampleLevel( BubbleFiltering, uv, 0 );
		if ( bm.r > 0.004 && g_flBubbles > 0.0 )
		{
			float code = round( bm.a * 255.0 );
			float rMax = floor( code / 16.0 ) + 0.5;
			float seed = code * 1.37 + 3.0;
			float lat = ( bm.g - 0.5 ) * 80.0;
			float y = uv.y * 1024.0;
			float grow = smoothstep( 0.0, 0.1, bm.b );
			float2 acc = 0.0;
			float2 bend = 0.0;
			[unroll] for ( int layer = 0; layer < 2; layer++ )
			{
				float cs = layer == 0 ? rMax * 2.6 : max( rMax * 0.95, 4.5 );
				float speed = ( layer == 0 ? 68.0 : 50.0 ) * g_flBubbleSpeed;
				float q = y + g_flTime * speed;
				float k0 = floor( q / cs );
				[unroll] for ( int j = -1; j <= 1; j++ )
				{
					float k = k0 + j;
					float2 s = float2( k, seed + layer * 17.0 );
					float h0 = Hash( s ), h1 = Hash( s + 3.1 ), h2 = Hash( s + 7.7 ), h3 = Hash( s + 11.3 ), h4 = Hash( s + 19.9 );
					if ( h0 > g_flBubbleDensity * ( layer == 0 ? 1.0 : 0.8 ) ) continue;
					float r = rMax * ( layer == 0 ? lerp( 0.5, 1.0, pow( h1, 1.5 ) ) : lerp( 0.1, 0.28, h1 ) ) * grow;
					float by = ( k + 0.5 + ( h2 - 0.5 ) * 0.3 ) * cs;
					float yb = by - g_flTime * speed;
					float zig = layer == 0 ? 0.35 : 0.6;
					float bl = ( h3 * 2.0 - 1.0 ) * rMax * ( layer == 0 ? 0.5 : 1.3 ) + sin( yb * 0.05 + h4 * 6.28 ) * rMax * zig;
					float2 b = Bubble( float2( lat - bl, q - by ), r, aa );
					if ( b.y > acc.y ) { acc = b; bend = float2( lat - bl, q - by ); }
				}
			}
			if ( acc.y > 0.0 )
			{
				// Linse: dahinter leicht vergrößert und aufgehellt
				float2 refr = uv - bend * 0.3 * float2( 1.0 / ( 1024.0 * g_flAspect ), 1.0 / 1024.0 );
				float3 behind = g_tScene.SampleGrad( SceneFiltering, refr + offset, uvDx, uvDy ).rgb * 1.08 + 0.03;
				float f = bm.r * saturate( g_flBubbles );
				lit = lerp( lit, behind, acc.y * 0.6 * f );
				lit = lerp( lit, float3( 0.9, 0.98, 1.0 ), saturate( acc.x * f * g_flBubbles ) );
				lit += 0.12 * acc.x * f * g_flBubbles;
			}
		}

		Material m = Material::Init( i );
		m.Albedo = saturate( lit );
		m.Emission = saturate( lit ) * g_flSelfIllumBrightness;
		m.Roughness = 0.5;
		m.Metalness = 0.0;
		m.Opacity = 1.0;
		return ShadingModelStandard::Shade( m );
	}
}
