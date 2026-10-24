HEADER
{
    Description = "First-person sleeves with separately authored close-up UV regions";
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

    CreateInputTexture2D( TextureSleeveLeft, Srgb, 8, "", "_sleeve_left", "Regions,30/10", Default3( 1, 1, 1 ) );
    CreateInputTexture2D( TextureSleeveRight, Srgb, 8, "", "_sleeve_right", "Regions,30/20", Default3( 1, 1, 1 ) );
    CreateInputTexture2D( TextureCuffMain, Srgb, 8, "", "_cuff_main", "Regions,30/30", Default3( 1, 1, 1 ) );
    CreateInputTexture2D( TextureCuffStrip, Srgb, 8, "", "_cuff_strip", "Regions,30/40", Default3( 1, 1, 1 ) );
    Texture2D g_tSleeveLeft < Channel( RGB, Box( TextureSleeveLeft ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tSleeveRight < Channel( RGB, Box( TextureSleeveRight ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tCuffMain < Channel( RGB, Box( TextureCuffMain ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tCuffStrip < Channel( RGB, Box( TextureCuffStrip ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    float g_flFineScale < Default( 12.0 ); Range( 1.0, 32.0 ); UiGroup( "Surface,20/30" ); >;
    float g_flFineNormalStrength < Default( 0.4 ); Range( 0.0, 1.0 ); UiGroup( "Surface,20/40" ); >;
    float g_flFineColourStrength < Default( 0.02 ); Range( 0.0, 0.1 ); UiGroup( "Surface,20/50" ); >;

    // Each image is authored over just this UV rectangle, rather than enlarged
    // inside a mostly unused full-shirt atlas. Explicit gradients retain proper
    // minification at the feathered boundaries and at grazing sleeve angles.
    float3 RegionColour( Texture2D image, float2 uv, float4 bounds, float3 previous )
    {
        float2 size = bounds.zw - bounds.xy;
        float2 regionUv = (uv - bounds.xy) / size;
        float2 edge = min( uv - bounds.xy, bounds.zw - uv );
        float weight = smoothstep( 0.0, 0.004, min( edge.x, edge.y ) );
        float3 colour = image.SampleGrad( TextureFiltering, regionUv, ddx( uv ) / size, ddy( uv ) / size ).rgb;
        return lerp( previous, colour, weight );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float2 uv = i.vTextureCoords.xy;
        float4 colour = g_tColor.SampleBias( TextureFiltering, uv, -0.65 );
        clip( colour.a - 0.5 );
        colour.rgb = RegionColour( g_tSleeveLeft, uv, float4( 0, 0, 0.52232856, 0.3197767 ), colour.rgb );
        colour.rgb = RegionColour( g_tSleeveRight, uv, float4( 0.4784689, 0, 1, 0.3197767 ), colour.rgb );
        colour.rgb = RegionColour( g_tCuffMain, uv, float4( 0.23923445, 0.27910686, 0.6379585, 0.53429025 ), colour.rgb );
        colour.rgb = RegionColour( g_tCuffStrip, uv, float4( 0.861244, 0.23923445, 1, 0.53429025 ), colour.rgb );
        m.Albedo = colour.rgb * g_flTintColor * i.vVertexColor.rgb;
        m.Opacity = colour.a;
        float2 fineUv = uv * g_flFineScale;
        float3 fine = DecodeNormal( g_tFineNormal.Sample( TextureFiltering, fineUv ).rgb );
        float3 folds = DecodeNormal( g_tNormal.SampleBias( TextureFiltering, uv, -0.35 ).rgb );
        float3 combined = normalize( float3( folds.xy + fine.xy * g_flFineNormalStrength, folds.z ) );
        m.Normal = TransformNormal( combined, i.vNormalWs, i.vTangentUWs, i.vTangentVWs );
        float2 data = g_tFineData.Sample( TextureFiltering, fineUv ).rg - 0.5;
        m.Albedo *= 1.0 + data.y * g_flFineColourStrength;
        m.Roughness = clamp( m.Roughness + data.x * 0.06, 0.55, 0.96 );
        m.Metalness = 0.0;
        return ShadingModelStandard::Shade( i, m );
    }
}
