HEADER
{
    Description = "Lowtide granite paving: original scan pixels, shallow relief and consistent filtering";
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
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float4 g_vPavingRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Paving" ); >;
    float2 g_vPavingScale < Default2( 1, 1 ); UiGroup( "Paving" ); >;

    float PavingNoise( float2 p )
    {
        float2 cell = floor( p ), f = frac( p );
        f = f * f * ( 3 - 2 * f );
        float4 h = float4( dot( cell, float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 0 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 0, 1 ), float2( 127.1, 311.7 ) ),
            dot( cell + 1, float2( 127.1, 311.7 ) ) );
        h = frac( sin( h ) * 43758.5453 );
        return lerp( lerp( h.x, h.y, f.x ), lerp( h.z, h.w, f.x ), f.y );
    }

    float PavingWetness( float2 ground )
    {
        // Rotated octaves break up the axis-aligned interpolation cells that
        // otherwise become visible as large square patches on the street.
        float2 a = float2( ground.x * .80 - ground.y * .60, ground.x * .60 + ground.y * .80 );
        float2 b = float2( ground.x * .36 + ground.y * .93, -ground.x * .93 + ground.y * .36 );
        float broad = PavingNoise( a / 270 + 13.7 );
        float medium = PavingNoise( b / 115 + 42.1 );
        float fine = PavingNoise( ground / 48 + 7.4 );
        float patches = broad * .48 + medium * .34 + fine * .18;
        return smoothstep( .31, .73, patches );
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        float2 repeat = input.vTextureCoords.xy * g_vPavingScale;
        float2 uv = g_vPavingRegion.xy + frac( repeat ) * g_vPavingRegion.zw;
        // Derivatives must be taken before frac: otherwise every atlas wrap
        // chooses a distant mip and paints a blurry line across the pavement.
        float2 dx = ddx( repeat ) * g_vPavingRegion.zw;
        float2 dy = ddy( repeat ) * g_vPavingRegion.zw;
        float4 color = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );
        Material material = Material::Init( input );
        material.Albedo = color.rgb * g_flTintColor * input.vVertexColor.rgb;
        material.Normal = TransformNormal( DecodeNormal( normal.xyz ), input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
        material.Roughness = rma.r;
        float2 ground = material.WorldPosition.xy;
        float wet = PavingWetness( ground );
        // Damp granite darkens and catches the sky without turning the whole
        // street into a mirror. Fine joints retain their roughness and normals.
        material.Albedo *= lerp( .91, 1.02, PavingNoise( ground / 390 + 9 ) );
        material.Albedo *= lerp( 1, .52, wet );
        material.Roughness = lerp( rma.r, max( .23, rma.r * .38 ), wet );
        material.Metalness = 0.0;
        material.AmbientOcclusion = rma.b;
        material.Opacity = 1.0;
        return ShadingModelStandard::Shade( input, material );
    }
}
