HEADER
{
    Description = "Lowtide tidal stone with physical-scale triplanar surfaces";
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"

    SamplerState StoneSampler < Filter( ANISO ); AddressU( WRAP ); AddressV( WRAP ); MaxAniso( 8 ); >;
    float g_flStoneTileInches < Default( 19.685 ); Range( 1, 100 ); >;
    float g_flStoneNormalStrength < Default( .6 ); Range( 0, 2 ); >;
    float2 g_vStoneRoughness < Default2( .82, .52 ); Range2( 0, 0, 1, 1 ); >;

    float2 StoneSlope( float2 uv )
    {
        float3 n = DecodeNormal( g_tNormal.Sample( StoneSampler, uv ).rgb );
        // Match the engine's normal-map Y convention, then convert the normal
        // into a surface slope rather than blending three axis normals.
        return float2( n.x, -n.y ) / max( n.z, .25 );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        float3 p = m.WorldPosition;
        float3 n = normalize( i.vNormalWs );
        float3 side = step( 0, n ) * 2 - 1;
        float3 weights = pow( abs( n ), 4 );
        weights /= max( dot( weights, 1 ), .00001 );
        float3 q = p / max( g_flStoneTileInches, 1 );
        // Right-handed projection bases on all six facing directions.
        float2 uvX = float2( q.y * side.x, q.z );
        float2 uvY = float2( -q.x * side.y, q.z );
        float2 uvZ = float2( q.x * side.z, q.y );
        float3 color = g_tColor.Sample( StoneSampler, uvX ).rgb * weights.x
                     + g_tColor.Sample( StoneSampler, uvY ).rgb * weights.y
                     + g_tColor.Sample( StoneSampler, uvZ ).rgb * weights.z;
        float2 x = StoneSlope( uvX );
        float2 y = StoneSlope( uvY );
        float2 z = StoneSlope( uvZ );
        float3 detail = float3( 0, x.x * side.x, x.y ) * weights.x
                      + float3( -y.x * side.y, 0, y.y ) * weights.y
                      + float3( z.x * side.z, z.y, 0 ) * weights.z;
        // A flat normal map must leave the authored smooth normal unchanged.
        detail -= n * dot( detail, n );
        m.Normal = normalize( n + detail * g_flStoneNormalStrength );
        float patina = .5 + .25*sin( p.x*.091 + p.y*.067 ) + .25*sin( p.x*.033 - p.y*.117 );
        float wet = 1 - smoothstep( -136, -125, p.z + (patina-.5)*3 );
        m.Albedo = color * g_flTintColor * lerp( .88, 1.05, patina ) * lerp( 1, .55, wet );
        m.Roughness = lerp( g_vStoneRoughness.x, g_vStoneRoughness.y, wet );
        m.Metalness = 0;
        m.Transmission = 0;
        m.Opacity = 1;
        m.AmbientOcclusion = 1;
        return ShadingModelStandard::Shade( i, m );
    }
}
