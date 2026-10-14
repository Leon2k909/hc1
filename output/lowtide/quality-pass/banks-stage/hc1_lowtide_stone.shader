HEADER
{
    Description = "Lowtide worn tidal cobbles";
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
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float3 p = m.WorldPosition;
        float patina = .5 + .25*sin( p.x*.091 + p.y*.067 ) + .25*sin( p.x*.033 - p.y*.117 );
        float wet = 1 - smoothstep( -136, -125, p.z + (patina-.5)*3 );
        m.Albedo *= lerp( .78, 1.05, patina ) * lerp( 1, .48, wet );
        m.Normal = normalize( lerp( normalize( i.vNormalWs ), m.Normal, .45 ) );
        m.Roughness = lerp( .78, .36, wet );
        m.Metalness = 0;
        m.Transmission = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
