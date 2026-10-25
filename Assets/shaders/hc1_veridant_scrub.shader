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
    #include "common/utils/Material.CommonInputs.hlsl"
    CreateInputTexture2D( TextureGrass, Srgb, 8, "", "_color", "Ground", Default4( 1, 1, 1, 1 ) );
    CreateInputTexture2D( TextureSoil, Srgb, 8, "", "_color", "Ground", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tGrass < Channel( RGB, Box( TextureGrass ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tSoil < Channel( RGB, Box( TextureSoil ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState GroundSampler < Filter( ANISOTROPIC ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/pixel.hlsl"
    float ScrubHash21( float2 p ) { return frac( sin( dot( p, float2(127.1,311.7) ) ) * 43758.5453 ); }
    float ScrubNoise( float2 p )
    {
        float2 a=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp( lerp(ScrubHash21(a),ScrubHash21(a+float2(1,0)),f.x), lerp(ScrubHash21(a+float2(0,1)),ScrubHash21(a+float2(1,1)),f.x), f.y );
    }
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float2 p = m.WorldPosition.xy;
        float broad = ScrubNoise(p/1100) * .60 + ScrubNoise(p/290) * .40;
        float patches = smoothstep(.36,.64,broad);
        float3 grass = g_tGrass.Sample(GroundSampler,p/128).rgb * float3(.90,.92,.78);
        float3 soil = g_tSoil.Sample(GroundSampler,p/192).rgb * float3(.62,.65,.52);
        float soilAmount = max(patches*.72,saturate((1-m.GeometricNormal.z)*2.5));
        m.Albedo = lerp(grass,soil,soilAmount) * lerp(.76,1.10,ScrubNoise(p/1600));
        m.Roughness = .98;
        m.Metalness = 0;
        CombinerInput combiner = ShadingModelStandard::MaterialToCombinerInput( m );
        LightingTerms_t lighting = InitLightingTerms();
        ComputeDirectLighting( lighting, combiner );
        CalculateIndirectLighting( lighting, combiner );
        float3 color = ( lighting.vDiffuse.rgb + lighting.vIndirectDiffuse.rgb ) * combiner.vDiffuseColor.rgb;
        if( DepthNormals::WantsDepthNormals() ) return DepthNormals::Output( m.Normal, m.Roughness, 1 );
        return DoAtmospherics( m.WorldPosition, m.ScreenPosition.xy, float4( color, 1 ) );
    }
}
