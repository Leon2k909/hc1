//=========================================================================================================================
// HC1 grime: blood and dirt over the first-person gun, gloves and sleeves (Code/Weapons/FirstPersonGrime.cs).
//
// Drawn as a second skin over each viewmodel renderer: the same model, pushed a hair out along its normals, and clear
// wherever it's clean. The pattern is laid out in the model's own space (inches, and the bind pose for a skinned mesh),
// so it sticks to the gun and the gloves as they move. FirstPersonGrime sets each skin's amounts every frame through
// its SceneObject's attributes:
//   GrimeBlood     how much blood is on it, 0-1: irregular splashes and fine spray, then pooled stains
//   GrimeBloodDry  how far it has dried, 0 wet (a deep glossy red) to 1 dry (a matte brown-black)
//   GrimeDirt      how much dirt, 0-1: dust in patches, more on the undersides, then caked on
//   GrimeDirtColor the dirt's colour, linear: the ground it came from (soil, sand, grass, concrete dust)
//   GrimeMud       how wet the dirt is: mud is darker and shinier
//   GrimeWet       rain on it, 0-1: everything glossier
//   GrimeSeed      a number of its own, so two guns don't wear the same splashes
//=========================================================================================================================
HEADER
{
	Description = "HC1 first-person grime: blood and dirt over a viewmodel";
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
	#define DEPTH_STATE_ALREADY_SET 1
	#define S_TRANSLUCENT 1
	#include "common/shared.hlsl"
}

struct VertexInput
{
	#include "common/vertexinput.hlsl"
};

struct PixelInput
{
	#include "common/pixelinput.hlsl"

	float3 vPositionOs : TEXCOORD8;
	float3 vNormalOs : TEXCOORD9;
};

//=========================================================================================================================

VS
{
	#include "common/vertex.hlsl"

	// How far out the skin sits over the surface it covers, in inches: enough that it never fights it for depth.
	float g_flPush < Default( 0.012 ); Range( 0.0, 0.2 ); UiGroup( "Grime,10/10" ); >;

	PixelInput MainVs( VertexInput i )
	{
		PixelInput o = ProcessVertex( i );

		float3 vNormalOs;
		float4 vTangentUOs_flTangentVSign;
		VS_DecodeObjectSpaceNormalAndTangent( i, vNormalOs, vTangentUOs_flTangentVSign );
		o.vPositionOs = i.vPositionOs.xyz;
		o.vNormalOs = vNormalOs;

		o.vPositionWs.xyz += normalize( o.vNormalWs.xyz ) * g_flPush;
		o.vPositionPs.xyzw = Position3WsToPs( o.vPositionWs.xyz );

		return FinalizeVertex( o );
	}
}

//=========================================================================================================================

PS
{
	#include "common/pixel.hlsl"

	BoolAttribute( DoNotCastShadows, true );
	RenderState( BlendEnable, true );
	RenderState( SrcBlend, SRC_ALPHA );
	RenderState( DstBlend, INV_SRC_ALPHA );
	RenderState( BlendOp, ADD );
	RenderState( SrcBlendAlpha, ONE );
	RenderState( DstBlendAlpha, INV_SRC_ALPHA );
	RenderState( BlendOpAlpha, ADD );
	RenderState( DepthEnable, true );
	RenderState( DepthFunc, GREATER_EQUAL );
	RenderState( DepthWriteEnable, false );

	float g_flBlood < Attribute( "GrimeBlood" ); Default( 0.0 ); >;
	float g_flBloodDry < Attribute( "GrimeBloodDry" ); Default( 0.0 ); >;
	float g_flDirt < Attribute( "GrimeDirt" ); Default( 0.0 ); >;
	float3 g_vDirtColor < Attribute( "GrimeDirtColor" ); Default3( 0.155, 0.09, 0.045 ); >;
	float g_flMud < Attribute( "GrimeMud" ); Default( 0.0 ); >;
	float g_flWet < Attribute( "GrimeWet" ); Default( 0.0 ); >;
	float g_flSeed < Attribute( "GrimeSeed" ); Default( 0.0 ); >;

	float Hash13( float3 p )
	{
		p = frac( p * 0.1031 );
		p += dot( p, p.zyx + 31.32 );
		return frac( ( p.x + p.y ) * p.z );
	}

	float3 Hash33( float3 p )
	{
		p = frac( p * float3( 0.1031, 0.1030, 0.0973 ) );
		p += dot( p, p.yxz + 33.33 );
		return frac( ( p.xxy + p.yxx ) * p.zyx );
	}

	float ValueNoise( float3 p )
	{
		float3 c = floor( p );
		float3 f = frac( p );
		f = f * f * ( 3.0 - 2.0 * f );
		float a = lerp( Hash13( c ), Hash13( c + float3( 1, 0, 0 ) ), f.x );
		float b = lerp( Hash13( c + float3( 0, 1, 0 ) ), Hash13( c + float3( 1, 1, 0 ) ), f.x );
		float d = lerp( Hash13( c + float3( 0, 0, 1 ) ), Hash13( c + float3( 1, 0, 1 ) ), f.x );
		float e = lerp( Hash13( c + float3( 0, 1, 1 ) ), Hash13( c + float3( 1, 1, 1 ) ), f.x );
		return lerp( lerp( a, b, f.y ), lerp( d, e, f.y ), f.z );
	}

	float Fbm( float3 p )
	{
		float sum = 0.0;
		float amplitude = 0.5;
		for ( int octave = 0; octave < 4; octave++ )
		{
			sum += amplitude * ValueNoise( p );
			p = p * 2.03 + 11.7;
			amplitude *= 0.5;
		}
		return sum / 0.9375;
	}

	// Each cell holds a randomly oriented, lobed splash with a narrow tail and satellite droplets. Noise breaks up
	// its outline and thickness; it is not an opaque sphere intersecting the surface. The whole stamp fits inside
	// its cell, so no neighbour search is needed. All coordinates remain in bind-pose model space.
	float Splashes( float3 p, float cell, float share, float minRadius, float maxRadius )
	{
		float3 q = p / cell;
		float3 id = floor( q );
		float3 h = Hash33( id );
		float radius = lerp( minRadius, maxRadius, h.x * h.x );
		float margin = min( radius * 2.5 + 0.015, 0.48 );
		float3 centre = margin + ( 1.0 - 2.0 * margin ) * Hash33( id + 5.31 );
		float3 axis = normalize( Hash33( id + 9.7 ) * 2.0 - 1.0 + 0.001 );
		float3 across = normalize( cross( axis, abs( axis.z ) < 0.9 ? float3( 0, 0, 1 ) : float3( 0, 1, 0 ) ) );
		float3 up = cross( axis, across );
		float3 offset = ( frac( q ) - centre ) / radius;
		float3 local = float3( dot( offset, axis ), dot( offset, across ), dot( offset, up ) );

		float core = length( local / float3( 1.1, 0.6, 0.85 ) );
		float tail = length( ( local - float3( 0.7, 0.24, 0.0 ) ) / float3( 1.15, 0.22, 0.4 ) );
		float lobe = length( ( local - float3( -0.4, 0.65, 0.1 ) ) / float3( 0.48, 0.5, 0.52 ) );
		float distance = min( core, min( tail, lobe ) );
		float edgeNoise = ValueNoise( q * 19.0 + 2.7 );
		float fineNoise = ValueNoise( q * 43.0 + 13.1 );
		distance += ( edgeNoise - 0.5 ) * 0.9 + ( fineNoise - 0.5 ) * 0.32;

		// Detached fine spray shares the same direction as the parent splash.
		float satellite = length( ( local - float3( 1.8, -0.65, 0.15 ) ) / float3( 0.23, 0.16, 0.19 ) );
		satellite = min( satellite, length( ( local - float3( -1.1, 1.4, -0.1 ) ) / float3( 0.13, 0.19, 0.14 ) ) );
		distance = min( distance, satellite );
		float edge = max( fwidth( distance ), 0.035 );
		float mask = 1.0 - smoothstep( 1.0 - edge, 1.0 + edge, distance );
		float thickness = ( 0.55 + 0.4 * h.z ) * lerp( 0.55, 1.0, saturate( ( 1.25 - distance ) * 1.5 ) );
		thickness *= lerp( 0.75, 1.05, edgeNoise );
		float cluster = lerp( 0.35, 1.2, ValueNoise( id * 0.31 + 4.8 ) );
		float there = step( Hash13( id * 1.71 + 2.9 ), share * cluster );
		return there * mask * thickness;
	}

	float4 MainPs( PixelInput i ) : SV_Target0
	{
		float3 p = i.vPositionOs + g_flSeed * 17.0;
		float3 n = normalize( i.vNormalOs );

		// Blood: clustered splashes and small spray, with thinner ragged stains as it accumulates.
		float blood = saturate( g_flBlood );
		float b = 0.0;
		if ( blood > 0.001 )
		{
			float pooling = Fbm( p * 0.85 ) + ( 0.5 - ValueNoise( p * 7.0 ) ) * 0.12;
			float poolEdge = max( fwidth( pooling ), 0.006 );
			float threshold = 0.83 - 0.23 * blood;
			float smear = smoothstep( threshold - poolEdge, threshold + poolEdge, pooling );
			smear *= smoothstep( 0.2, 0.65, ValueNoise( p * 19.0 ) ) * ( 0.2 + 0.5 * ValueNoise( p * 3.0 ) );
			smear *= smoothstep( 0.35, 0.85, blood );
			float drops = Splashes( p, 0.65, blood * 0.7, 0.1, 0.18 );
			drops = max( drops, Splashes( p + 3.1, 0.26, blood * 0.85, 0.08, 0.18 ) );
			drops = max( drops, Splashes( p + 7.7, 0.12, blood * 0.65, 0.08, 0.16 ) );
			b = saturate( max( smear, drops ) );
		}

		// Dirt: dust in patches, more on the undersides, fine grains and then a caked layer as it builds up.
		float dirt = saturate( g_flDirt );
		float d = 0.0;
		if ( dirt > 0.001 )
		{
			float patches = Fbm( p * 0.6 ) * 0.65 + ValueNoise( p * 2.4 ) * 0.35 + saturate( -n.z ) * 0.2;
			d = smoothstep( 0.0, 0.2, patches - ( 0.95 - 0.7 * dirt ) ) * ( 0.55 + 0.45 * dirt );
			float grain = Hash13( floor( p * 40.0 ) );
			d = saturate( d + step( 1.0 - 0.3 * dirt, grain ) * 0.6 * dirt );
		}

		float alpha = saturate( b + d * ( 1.0 - b ) );
		clip( alpha - 0.002 );
		float bloodShare = saturate( b / max( alpha, 0.0001 ) );

		float dry = saturate( g_flBloodDry );
		float thickness = saturate( b * 0.9 + ValueNoise( p * 5.0 ) * 0.25 );
		float3 wetBlood = lerp( float3( 0.12, 0.005, 0.003 ), float3( 0.045, 0.0016, 0.001 ), thickness );
		float3 bloodColor = lerp( wetBlood, float3( 0.028, 0.009, 0.006 ), dry );
		float bloodRoughness = lerp( 0.27 + 0.16 * ( 1.0 - b ), 0.78, dry );
		float mud = saturate( g_flMud );
		float3 dirtColor = g_vDirtColor * lerp( 0.75, 1.2, ValueNoise( p * 1.3 ) ) * lerp( 1.0, 0.6, mud );
		float dirtRoughness = lerp( 0.92, 0.45, mud );

		Material m = Material::Init( i );
		m.Albedo = lerp( dirtColor, bloodColor, bloodShare );
		m.Normal = normalize( i.vNormalWs );
		m.Roughness = lerp( dirtRoughness, bloodRoughness, bloodShare ) * lerp( 1.0, 0.5, saturate( g_flWet ) );
		m.Metalness = 0.0;
		m.AmbientOcclusion = 1.0;
		m.Opacity = 1.0;
		float3 colour = ShadingModelStandard::Shade( i, m ).rgb;

		// The blood mask already includes its local thickness, so thinner spray reveals the underlying finish.
		return float4( colour, alpha * lerp( lerp( 0.8, 1.0, dirt ), 1.0, bloodShare ) );
	}
}
