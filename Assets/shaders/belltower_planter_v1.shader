HEADER
{
    Description = "Belltower cut planter stone and compost: physical mesh edges, restrained scan normals";
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
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float g_flPlanterNormal < Default( .45 ); Range( 0, 1 ); UiGroup( "Stone,20/10" ); >;
    float g_flPlanterAo < Default( .72 ); Range( 0, 1 ); UiGroup( "Stone,20/20" ); >;
    float g_flPlanterRoughness < Default( .72 ); Range( .3, 1 ); UiGroup( "Stone,20/30" ); >;
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        #if !S_MODE_DEPTH
        float2 uv = i.vTextureCoords.xy;
        float4 color = g_tColor.Sample( TextureFiltering, uv );
        float4 normal = g_tNormal.Sample( TextureFiltering, uv );
        float4 rma = g_tRma.Sample( TextureFiltering, uv );
        m.Albedo = color.rgb * g_flTintColor * i.vVertexColor.rgb;
        float3 tangentNormal = DecodeNormal( normal.xyz );
        tangentNormal.xy *= g_flPlanterNormal;
        tangentNormal = normalize( tangentNormal );
        m.Normal = TransformNormal( tangentNormal, i.vNormalWs, i.vTangentUWs, i.vTangentVWs );
        m.Roughness = max( g_flPlanterRoughness, rma.r );
        m.AmbientOcclusion = lerp( 1.0, rma.b, g_flPlanterAo );
        m.TintMask = normal.a;
        m.TextureCoords = uv;
        #endif
        m.Metalness = 0;
        m.Transmission = 0;
        m.Opacity = 1;
        return ShadingModelStandard::Shade( i, m );
    }
}
