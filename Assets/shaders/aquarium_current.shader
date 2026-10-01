// Lebendiges Endbeckenbild end_scene_color.png (Schatzkiste und Säulenruine, erzeugt von tools/aquarium/tex/end_scene.js).
// end_scene_motion.png sagt, was sich wo bewegt (u rechts, v unten):
//   R  Ausschlag der Pflanzen (0 am Fuß, 1 an der Spitze)   G  Phase der Pflanzengruppe
//   B  feste Dinge (Felsen, Ruine, Kiste, Korallen)          A  oben freies Wasser, unten heller Sand
// Tang und Seegras wiegen sich in der Strömung, ohne feste Dinge mitzuziehen; die Oberfläche kräuselt sich, die
// Lichtstrahlen flackern leicht, Schwebteilchen steigen auf und über den Sand wandert ein Lichtnetz.
HEADER
{
	Description = "Endbecken: Pflanzen in der Strömung, bewegtes Wasser und Licht";
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

	// Box-Filter statt AlphaWeighted: funktioniert bei jeder Bildgröße.
	CreateInputTexture2D( TextureColor, Srgb, 8, "", "_color", "Material,10/10", Default3( 1.0, 1.0, 1.0 ) );
	CreateInputTexture2D( TextureMotion, Linear, 8, "", "_motion", "Material,10/15", Default4( 0.0, 0.5, 0.0, 0.0 ) );
	Texture2D g_tScene < Channel( RGB, Box( TextureColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
	Texture2D g_tMotion < Channel( RGBA, Box( TextureMotion ), Linear ); OutputFormat( RGBA8888 ); SrgbRead( false ); >;
	SamplerState SceneFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( CLAMP ); AddressV( CLAMP ); >;
	SamplerState MotionFiltering < Filter( BILINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
	TextureAttribute( LightSim_DiffuseAlbedoTexture, g_tScene );
	TextureAttribute( RepresentativeTexture, g_tScene );
	float g_flSelfIllumBrightness < Default( 0.55 ); Range( 0.0, 4.0 ); UiGroup( "Material,10/20" ); >;

	float g_flCurrentStrength < Default( 0.013 ); Range( 0.0, 0.03 ); UiGroup( "Stroemung,10/10" ); >;
	float g_flCurrentSpeed < Default( 0.8 ); Range( 0.0, 2.0 ); UiGroup( "Stroemung,10/20" ); >;
	float g_flSurfaceRipple < Default( 0.003 ); Range( 0.0, 0.01 ); UiGroup( "Stroemung,10/30" ); >;
	float g_flRayFlicker < Default( 0.1 ); Range( 0.0, 0.5 ); UiGroup( "Wasser,20/10" ); >;
	float g_flCaustics < Default( 0.3 ); Range( 0.0, 1.0 ); UiGroup( "Wasser,20/20" ); >;
	float g_flParticles < Default( 0.35 ); Range( 0.0, 1.0 ); UiGroup( "Wasser,20/30" ); >;

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

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		float2 uv = i.vTextureCoords.xy;
		float t = g_flTime * g_flCurrentSpeed + 40.0;
		float4 mk = g_tMotion.Sample( MotionFiltering, uv );

		// Pflanzen: die Biegung läuft vom Fuß zur Spitze, jede Gruppe mit eigener Phase.
		float ph = mk.g * 6.2832;
		float wave = 0.7 * sin( t + ph - uv.y * 3.0 ) + 0.3 * sin( t * 1.63 + ph * 2.0 + uv.x * 25.0 - uv.y * 5.0 );
		float2 offset = float2( wave, 0.15 * cos( t * 0.9 + ph - uv.y * 3.0 ) ) * mk.r * g_flCurrentStrength;

		// Wasseroberfläche kräuselt sich (nur im freien Wasser)
		float top = 1.0 - smoothstep( 0.1, 0.22, uv.y );
		offset += float2( sin( t * 0.8 + uv.x * 23.0 + uv.y * 40.0 ) + 0.5 * sin( t * 1.3 - uv.x * 41.0 ),
			0.6 * sin( t * 1.1 + uv.x * 31.0 ) ) * top * mk.a * g_flSurfaceRipple;

		offset *= smoothstep( 0.0, 0.02, uv.x ) * smoothstep( 0.0, 0.02, 1.0 - uv.x );
		// Nie aus festen Dingen lesen: sonst würden Ruine oder Kiste in die Pflanzen hineinwachsen.
		offset *= 1.0 - g_tMotion.Sample( MotionFiltering, uv + offset ).b;

		i.vTextureCoords.xy = saturate( uv + offset );
		float3 color = g_tScene.Sample( SceneFiltering, i.vTextureCoords.xy ).rgb;

		// Lichtstrahlen aus der Sonne über der Bildmitte flackern breit und langsam.
		float2 d = float2( ( uv.x - 0.5 ) * 1.5, uv.y + 0.12 );
		float ang = atan2( d.x, d.y );
		float shafts = sin( ang * 9.0 + t * 0.3 ) * ( 0.6 + 0.4 * sin( ang * 4.0 - t * 0.17 + 1.3 ) );
		float lum = dot( color, float3( 0.3, 0.5, 0.2 ) );
		float ray = saturate( ( lum - 0.45 ) * 2.2 ) * smoothstep( 0.06, 0.14, uv.y ) * ( 1.0 - smoothstep( 0.35, 0.75, uv.y ) );
		float3 lit = color * ( 1.0 + g_flRayFlicker * ray * shafts );

		// Lichtnetz auf dem Sand, perspektivisch zum Horizont hin enger
		float bottom = smoothstep( 0.74, 0.84, uv.y ) * mk.a;
		float depth = 1.0 / max( uv.y - 0.6, 0.02 );
		float caustic = Caustic( float2( ( uv.x - 0.5 ) * depth * 3.36, depth * 1.2 ), t * 0.5 );
		lit += color * caustic * bottom * g_flCaustics;

		// Schwebteilchen im freien Wasser
		float open = mk.a * ( 1.0 - smoothstep( 0.6, 0.75, uv.y ) );
		float specks = Particles( uv, t, 18.0, 0.35, 0.0 ) + 0.6 * Particles( uv, t, 30.0, 0.22, 5.0 );
		lit += float3( 0.7, 0.9, 1.0 ) * specks * open * g_flParticles;

		Material m = Material::Init( i );
		m.Albedo = saturate( lit );
		m.Emission = saturate( lit ) * g_flSelfIllumBrightness;
		m.Roughness = 0.5;
		m.Metalness = 0.0;
		m.Opacity = 1.0;
		return ShadingModelStandard::Shade( m );
	}
}
