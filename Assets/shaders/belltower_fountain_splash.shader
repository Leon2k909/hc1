HEADER
{
    Description = "Soft broken fountain froth with drifting bubbles";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
}
COMMON
{
    #define S_SPECULAR 1
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
    PixelInput MainVs( VertexInput i )
    {
        return FinalizeVertex( ProcessVertex( i ) );
    }
}
PS
{
    #define S_TRANSLUCENT 1
    #define BLEND_MODE_ALREADY_SET 1
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( DepthWriteEnable, false );
    #include "common/pixel.hlsl"
    SamplerState FoamSampler < Filter( ANISO ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    CreateInputTexture2D( SplashMask, Linear, 8, "", "_mask", "Water", Default3( 0, 0, 0 ) );
    Texture2D MaskTexture < Channel( R, Box( SplashMask ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float2 uv = i.vTextureCoords.xy;
        float2 drift = float2(sin(uv.y*21+g_flTime*.9),cos(uv.x*17-g_flTime*.7))*.019;
        float mask = MaskTexture.Sample(FoamSampler, uv+drift).r;
        float bubbles = sin(uv.x*107+g_flTime*2.1)*sin(uv.y*93-g_flTime*1.7);
        m.Albedo = float3(.66,.76,.77);
        m.Roughness = .30;
        m.Metalness = 0;
        m.AmbientOcclusion = 1;
        m.Opacity = mask * (.64+.12*bubbles);
        return ShadingModelStandard::Shade(i, m);
    }
}
