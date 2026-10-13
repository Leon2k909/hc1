HEADER
{
	Description = "Grenade smoke: depth-clipped puff volumes after world transparency";
}

MODES
{
	Forward();
}

FEATURES
{
	#include "common/features.hlsl"
}

COMMON
{
	#include "common/shared.hlsl"

	struct SmokePuff
	{
		float4 CentreRadius;
		float4 ColourOpacity;
	};
	StructuredBuffer<SmokePuff> g_SmokePuffs < Attribute( "SmokePuffs" ); >;
}

struct VS_INPUT
{
	float3 vPositionOs : POSITION < Semantic( PosXyz ); >;
};

struct PixelInput
{
	#if PROGRAM == VFX_PROGRAM_VS
		float4 vPositionPs : SV_Position;
	#else
		float4 vPositionSs : SV_Position;
	#endif
	nointerpolation uint puffIndex : TEXCOORD0;
};

VS
{
	PixelInput MainVs( VS_INPUT input, uint instanceIndex : SV_InstanceID )
	{
		SmokePuff puff = g_SmokePuffs[instanceIndex];
		float3 relative = puff.CentreRadius.xyz - g_vCameraPositionWs;
		float radius = puff.CentreRadius.w;
		float3 forward = g_vCameraDirWs;
		float3 up = g_vCameraUpDirWs;
		float3 right = normalize( cross( forward, up ) );
		float2 low = -1.0;
		float2 high = 1.0;

		// Project a containing box to bound the sphere. A puff crossing the camera/near plane uses the full viewport;
		// the ray integral still clips it precisely. This also keeps smoke visible while the camera is inside it.
		if ( dot( relative, forward ) > radius + g_flNearPlane )
		{
			low = 1.0;
			high = -1.0;
			[unroll]
			for ( uint k = 0; k < 8; k++ )
			{
				float3 corner = puff.CentreRadius.xyz + radius *
					(right * ((k & 1) ? 1.0 : -1.0) + up * ((k & 2) ? 1.0 : -1.0) + forward * ((k & 4) ? 1.0 : -1.0));
				float4 projected = Position3WsToPs( corner );
				float2 ndc = projected.xy / projected.w;
				low = min( low, ndc );
				high = max( high, ndc );
			}
			low = max( low, -1.0 );
			high = min( high, 1.0 );
		}

		float2 cornerUv = input.vPositionOs.xy * 0.5 + 0.5;
		PixelInput output;
		output.vPositionPs = float4( lerp( low, high, cornerUv ), 0.0, 1.0 );
		output.puffIndex = instanceIndex;
		return output;
	}
}

PS
{
	#define CUSTOM_MATERIAL_INPUTS 1
	#define DEPTH_STATE_ALREADY_SET 1
	#define BLEND_MODE_ALREADY_SET 1
	#include "common/classes/Depth.hlsl"
	#include "common/classes/Fog.hlsl"

	// This is a volume integration, not a flat card's depth test. Clip the ray at opaque scene depth below.
	// Never write puff depth: a transparent edge must not occlude another puff or later scene geometry.
	RenderState( DepthEnable, false );
	RenderState( DepthWriteEnable, false );
	RenderState( CullMode, NONE );
	RenderState( BlendEnable, true );
	RenderState( SrcBlend, SRC_ALPHA );
	RenderState( DstBlend, INV_SRC_ALPHA );
	RenderState( SrcBlendAlpha, ONE );
	RenderState( DstBlendAlpha, INV_SRC_ALPHA );

	float Integral( float u, float heightSquared )
	{
		return u * (heightSquared * heightSquared - u * u * (2.0 / 3.0) * heightSquared + u * u * u * u / 5.0);
	}

	float4 MainPs( PixelInput input ) : SV_Target0
	{
		SmokePuff puff = g_SmokePuffs[input.puffIndex];
		float2 screen = input.vPositionSs.xy;
		float2 ndc = screen * g_vInvViewportSize * float2( 2.0, -2.0 ) + float2( -1.0, 1.0 );
		float4 projectedRay = mul( g_matProjectionToWorld, float4( ndc, 1.0, 1.0 ) );
		float3 nearPosition = projectedRay.xyz / projectedRay.w;
		float3 origin = g_vCameraPositionWs;
		float3 ray = normalize( nearPosition );
		if ( abs( g_matViewToProjection[3][3] ) > 0.5 )
		{
			// Orthographic cameras have parallel rays starting at different points on the camera plane.
			ray = g_vCameraDirWs;
			origin += nearPosition - ray * dot( nearPosition, ray );
		}
		float surfaceDistance = 1e6;
		if ( Depth::GetNormalized( screen ) > 0.0 )
			surfaceDistance = max( 0.0, dot( Depth::GetWorldPosition( screen ) - origin, ray ) );

		float radius = puff.CentreRadius.w;
		float3 offset = puff.CentreRadius.xyz - origin;
		float along = dot( offset, ray );
		float perpendicularSquared = max( 0.0, dot( offset, offset ) - along * along );
		float heightSquared = 1.0 - perpendicularSquared / (radius * radius);
		if ( heightSquared <= 0.0 ) discard;
		float height = sqrt( heightSquared );
		float start = max( -height, -along / radius );
		float end = min( height, (surfaceDistance - along) / radius );
		if ( end <= start ) discard;
		float path = max( 0.0, (Integral( end, heightSquared ) - Integral( start, heightSquared )) * (15.0 / 16.0) );
		float opticalDepth = -log( 1.0 - min( puff.ColourOpacity.a, 0.995 ) ) * path;

		// Gentle spatial detail, shared by neighbouring puffs. No frame-random offsets or camera-facing texture flips.
		float3 samplePosition = origin + ray * max( along, 0.0 );
		float detail = sin( samplePosition.x * 0.085 + samplePosition.z * 0.043 )
			* sin( samplePosition.y * 0.073 - samplePosition.z * 0.057 );
		float alpha = 1.0 - exp( -opticalDepth * (1.0 + detail * 0.12) );
		float3 colour = puff.ColourOpacity.rgb;
		return float4( Fog::Apply( puff.CentreRadius.xyz, screen, colour ), alpha );
	}
}
