HEADER
{
    Description = "Belltower grocery displays: controlled opaque PBR surfaces";
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
    // Opaque RGB mips preserve the unmodified non-power-of-two label artwork.
    #define AlphaWeighted( color, opacity ) Box( color )
    #include "common/utils/Material.CommonInputs.hlsl"
    #undef AlphaWeighted
    #include "common/pixel.hlsl"

    float3 g_vShopTint < Default3(1,1,1); UiType(Color); >;
    float g_flShopRoughness < Default(.7); Range(.05,1); >;
    float g_flShopMetalness < Default(0); Range(0,1); >;
    float g_flShopNormal < Default(.4); Range(0,1); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init(i);
        #if !S_MODE_DEPTH
        float2 uv = i.vTextureCoords.xy;
        float4 colour = g_tColor.Sample(TextureFiltering,uv);
        float4 normal = g_tNormal.Sample(TextureFiltering,uv);
        float4 rma = g_tRma.Sample(TextureFiltering,uv);
        m.Albedo = saturate(colour.rgb * g_vShopTint * i.vVertexColor.rgb);
        float3 n = DecodeNormal(normal.xyz);
        n.xy *= g_flShopNormal;
        m.Normal = TransformNormal(normalize(n),i.vNormalWs,i.vTangentUWs,i.vTangentVWs);
        m.Roughness = clamp(rma.r * g_flShopRoughness,.06,.98);
        m.AmbientOcclusion = lerp(1.0,rma.b,.35);
        m.TextureCoords = uv;
        #endif
        m.Metalness = g_flShopMetalness;
        m.Transmission = 0;
        m.Opacity = 1;
        return ShadingModelStandard::Shade(i,m);
    }
}
