HEADER
{
    Description = "Veridant rolling scrub soil with broad natural variation";
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
    #include "common/pixel.hlsl"
    #if ( S_MODE_DEPTH == 0 )
        RenderState( DepthFunc, EQUAL );
        RenderState( DepthWriteEnable, false );
    #endif
    CreateInputTexture2D( TextureGrass, Srgb, 8, "", "_color", "Ground", Default4( 1, 1, 1, 1 ) );
    CreateInputTexture2D( TextureSoil, Srgb, 8, "", "_color", "Ground", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tGrass < Channel( RGB, Box( TextureGrass ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tSoil < Channel( RGB, Box( TextureSoil ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState GroundSampler < Filter( ANISOTROPIC ); AddressU( WRAP ); AddressV( WRAP ); >;
    #if ( S_MODE_DEPTH == 0 )
        [earlydepthstencil]
    #endif
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        m.Normal = normalize(i.vNormalWs.xyz);
        float2 p = m.WorldPosition.xy;
        float3 broad = g_tGrass.Sample(GroundSampler,p/6500+float2(.13,.27)).rgb;
        float3 medium = g_tGrass.Sample(GroundSampler,p/2200+float2(.71,.19)).rgb;
        float patches = smoothstep(.06,.14,broad.g*.65+medium.g*.35);
        float3 grass = g_tGrass.Sample(GroundSampler,p/128).rgb * float3(.90,.92,.78);
        float3 soil = g_tSoil.Sample(GroundSampler,p/192).rgb * float3(.62,.65,.52);
        float soilAmount = max(patches*.55,smoothstep(.10,.43,1-saturate(m.Normal.z)));
        m.Albedo = lerp(grass,soil,soilAmount) * lerp(.82,1.08,saturate(broad.g*6));
        m.Roughness = .98;
        m.Metalness = 0;
        return ShadingModelStandard::Shade(i,m);
    }
}
