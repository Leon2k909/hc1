// Scoped teammate variant of the engine object-highlight shader.
MODES
{
	Forward();
	Depth(); // It was doing this before, is it correct?
}

FEATURES
{
    #include "common/features.hlsl"
    Feature( F_USE_PATTERN, 0..1, "Rendering" );
}

COMMON
{
	#define USE_CUSTOM_SHADING
	#include "common/shared.hlsl"

	DynamicCombo( D_OUTLINE_PASS, 0..1, Sys( ALL ) );
	
	#define OUTLINE_INSIDE 0
	#define OUTLINE_OUTSIDE 1
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
	//
	// Main
	//
	PixelInput MainVs( VertexInput i )
	{
		PixelInput o = ProcessVertex( i );
		return FinalizeVertex( o );
	}
}

//
// Used for outline
//
GS
{
#if D_OUTLINE_PASS == OUTLINE_OUTSIDE

	float _LineSize < UiType( Color ); UiGroup( "Color" ); Attribute( "LineWidth" ); Default( 0.2f ); >;

	#include "common/vertex.hlsl"

	void PositionOffset (inout PixelInput input, float2 vOffsetDir, float flOutlineSize)
	{
		float2 vAspectRatio = normalize(g_vInvViewportSize);
		input.vPositionPs.xy += (vOffsetDir * 2.0) * vAspectRatio * input.vPositionPs.w * flOutlineSize;

		// even though we do -f-vk-invert this is the only shader that does not behave with it
		#if defined( VULKAN )
			input.vPositionPs.y = -input.vPositionPs.y;
		#endif
	}

    //
    // Main
    //
    [maxvertexcount(3*7)]
    void MainGs(triangle in PixelInput vertices[3], inout TriangleStream<PixelInput> triStream)
    {
		const float flOutlineSize = _LineSize / 64.0f;
        const float fTwoPi = 6.28318f;
		const int nNumIterations = clamp( _LineSize * 10, 3, 6 ); // Thin lines don't need many iterations 

        PixelInput v[3];

        [unroll]
        for( float i = 0; i <= nNumIterations; i += 1 )
		{
			float fCycle = i / nNumIterations;

			float2 vOffset = float2( 
				( sin( fCycle * fTwoPi ) ),
				( cos( fCycle * fTwoPi ) )
			);

			for ( int i = 0; i < 3; i++ )
			{
				v[i] = vertices[i];
				PositionOffset( v[i], vOffset, flOutlineSize );
			}

			triStream.Append(v[2]);
			triStream.Append(v[0]);
			triStream.Append(v[1]);
		}
		
		// emit the vertices
		triStream.RestartStrip();
    }
#endif
}

PS
{
	#include "common.fxc"
	#include "common/classes/Depth.hlsl"
	StaticCombo( S_USE_PATTERN, F_USE_PATTERN, Sys( ALL ) );

    RenderState( DepthWriteEnable, true );
    RenderState( DepthEnable, true );
	RenderState( ColorWriteEnable0, RGBA );

	RenderState( CullMode, BACK );

	RenderState( StencilEnable, true );
	RenderState( StencilRef, 1 );

	// Write to stencil if we're doing the inside pass
#if D_OUTLINE_PASS == OUTLINE_INSIDE
	RenderState( StencilPassOp, REPLACE );
	RenderState( BackStencilPassOp, REPLACE );
	RenderState( StencilFunc, ALWAYS );
	RenderState( BackStencilFunc, ALWAYS );
#else
	RenderState( StencilPassOp, KEEP );
	RenderState( StencilFunc, NOT_EQUAL );
	RenderState( BackStencilFunc, NOT_EQUAL );
#endif

	Texture2D _BaseOpacity < Attribute( "BaseOpacity" ); >;
	Texture2D _ColorTexture < Attribute( "ColorTexture" ); SrgbRead( true ); >;

	float4 _ColorMain < UiType( Color ); UiGroup( "Color" ); Attribute( "Color" ); >;
	float4 _ColorOccluded < UiType( Color ); UiGroup( "Color" ); Attribute( "ObscuredColor" ); >;

	float2 g_vPatternScrollRate < Default2( 0.0, 0.0 ); Range2( -2.0, -2.0, 2.0, 2.0 ); UiGroup( "Pattern,11/1" ); >;

    CreateInputTexture2D( Pattern, Linear, 8, "", "",  "Pattern,11/2", Default( 1.0 ) );
    Texture2D g_tPattern < Channel( R, Box( Pattern ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
	

	// The scene's distance at a pixel. The private highlight target uses projection
	// Z already; only the sampled scene depth needs the scene's layer range.
	float CoverDistance( float2 pixel )
	{
		pixel = clamp( pixel, 0.0f, 1.0f / g_vInvViewportSize - 1.0f );
		float depth = Depth::Get( pixel );
		float layer = ( depth - g_flViewportMinZ ) / ( g_flViewportMaxZ - g_flViewportMinZ );
		return Depth::Linearize( saturate( layer ), pixel );
	}
	//
	// Main
	//
	float4 MainPs( PixelInput i ): SV_Target
	{
        // A pixel is hidden only where cover stands in front of the character across
        // its whole 3x3 neighbourhood. A single depth tap reads the nearer surface
        // at the character's own depth edges (a vest's hem over the shirt, belts,
        // pockets) and on sloped triangles, which lit visible teammates.
        float2 pixelPosition = i.vPositionSs.xy - g_vViewportOffset;
        float2 screenUv = CalculateViewportUv( i.vPositionSs.xy );
        float objectDistance = Depth::Linearize( i.vPositionSs.z, pixelPosition );
        float coverDistance = 0.0f;
        [unroll] for ( int y = -1; y <= 1; y++ )
            [unroll] for ( int x = -1; x <= 1; x++ )
                coverDistance = max( coverDistance, CoverDistance( pixelPosition + float2( x, y ) ) );
        // About a pixel and a half of world size at that distance, for LOD and
        // depth precision, and never under a quarter inch.
        float pixelSize = objectDistance * 2.0f * g_vInvViewportSize.y / g_matViewToProjection[1][1];
        bool hidden = objectDistance > coverDistance + max( 0.25f, pixelSize * 1.5f );
        float4 vColor = hidden ? _ColorOccluded : _ColorMain;

		// Add pattern to alpha
		#if ( S_USE_PATTERN == 1 )
		{
			float2 vPatternDims = TextureDimensions2D( g_tPattern, 0 ).xy;
			float fPattern = g_tPattern.Sample( g_sPointWrap, i.vPositionSs.xy / vPatternDims + ( g_vPatternScrollRate * g_flTime ) ).r;
			vColor.a *= fPattern;
		}
		#endif

		// We do custom blending here to avoid overdraw
		float4 vScene = _ColorTexture.Sample( g_sPointWrap, screenUv );
		float flBlend = saturate( vColor.a );
		vColor.rgb = lerp( vScene.rgb, vColor.rgb, flBlend );

		// Composite alpha over the scene so outlines stay visible on cameras with a transparent background
		vColor.a = lerp( vScene.a, 1.0f, flBlend );

		return vColor;
	}
}