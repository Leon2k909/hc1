HEADER
{
    Description = "Lowtide weathered harbour timber";
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
        float weather = .5 + .25*sin( p.x*.095 + p.y*.11 ) + .25*sin( p.z*.067 + p.y*.22 );
        float damp = 1 - smoothstep( -135, -72, p.z + (weather-.5)*10 );
        float tide = (1-smoothstep( -96, -52, p.z )) * smoothstep( -141, -130, p.z );
        m.Albedo *= lerp( .78, 1.08, weather ) * lerp( 1, .52, damp );
        m.Albedo *= lerp( float3(1, 1, 1), float3(.71, .77, .62), tide*.55 );
        m.Roughness = lerp( m.Roughness, .49, damp );
        m.Metalness = 0;
        m.Transmission = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
