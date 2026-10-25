HEADER
{
    Description = "First-person garments: preserved tailoring with independent fine surface detail";
    Version = 1;
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth();
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
    #define CUSTOM_TEXTURE_FILTERING
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 16 ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"

    CreateInputTexture2D( TextureFineNormal, Linear, 8, "NormalizeNormals", "_fine_normal", "Surface,20/10", Default3( 0.5, 0.5, 1.0 ) );
    CreateInputTexture2D( TextureFineData, Linear, 8, "", "_fine_data", "Surface,20/20", Default3( 0.5, 0.5, 0.5 ) );
    Texture2D g_tFineNormal < Channel( RGB, Box( TextureFineNormal ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    Texture2D g_tFineData < Channel( RGB, Box( TextureFineData ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    float g_flFineScale < Default( 12.0 ); Range( 1.0, 32.0 ); UiGroup( "Surface,20/30" ); >;
    float g_flFineNormalStrength < Default( 0.45 ); Range( 0.0, 1.0 ); UiGroup( "Surface,20/40" ); >;
    float g_flFineColourStrength < Default( 0.025 ); Range( 0.0, 0.1 ); UiGroup( "Surface,20/50" ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float4 colour = g_tColor.SampleBias( TextureFiltering, i.vTextureCoords.xy, -0.65 );
        // The common material helper supplies opacity but does not discard
        // transparent garment triangles for a custom pixel shader.
        clip( colour.a - 0.5 );
        m.Albedo = colour.rgb * g_flTintColor * i.vVertexColor.rgb;
        m.Opacity = colour.a;
        float2 fineUv = i.vTextureCoords.xy * g_flFineScale;
        float3 fine = DecodeNormal( g_tFineNormal.Sample( TextureFiltering, fineUv ).rgb );
        float3 base = DecodeNormal( g_tNormal.SampleBias( TextureFiltering, i.vTextureCoords.xy, -0.35 ).rgb );
        // Small tangent-space slopes retain the garment's folds and seam normals.
        float3 combined = normalize( float3( base.xy + fine.xy * g_flFineNormalStrength, base.z ) );
        m.Normal = TransformNormal( combined, i.vNormalWs, i.vTangentUWs, i.vTangentVWs );
        float2 data = g_tFineData.Sample( TextureFiltering, fineUv ).rg - 0.5;
        m.Albedo *= 1.0 + data.y * g_flFineColourStrength;
        m.Roughness = clamp( m.Roughness + data.x * 0.08, 0.45, 0.96 );
        m.Metalness = 0.0;
        return ShadingModelStandard::Shade( i, m );
    }
}
