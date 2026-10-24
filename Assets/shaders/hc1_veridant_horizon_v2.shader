HEADER
{
    Description = "Veridant fixed distant horizon with opaque joined ridges";
}
FEATURES
{
    #include "common/features.hlsl"
    Feature( F_ALPHA_TEST, 0..1, "Rendering" );
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
    CreateInputTexture2D( TextureVista, Srgb, 8, "", "_color", "Vista", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tVista < Channel( RGBA, Box( TextureVista ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState VistaSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flVistaBrightness < Default(1.0); >;
    float g_flImageU0 < Default(0.0); >;
    float g_flImageU1 < Default(1.0); >;
    float g_flCoastSide < Default(0.0); >;
    float g_flSector < Default(0.0); >;
    float g_flPixelScale < Default(14.0); >;
    float g_flAtlasWidth < Default(1254.0); >;
    float g_flAtlasHeight < Default(1254.0); >;
    float4 g_vAtlasRect0 < Default4(8,220,1246,427); >;
    float4 g_vAtlasRect1 < Default4(8,998,1246,1188); >;
    float4 g_vAtlasRect2 < Default4(8,649,1246,833); >;
    float g_flBottom0 < Default(0.0); >;
    float g_flBottom1 < Default(0.0); >;
    float g_flBottom2 < Default(0.0); >;
    #undef MATERIAL_ALPHA_TEXTURE
    #define MATERIAL_ALPHA_TEXTURE g_tVista
    #include "common/pixel.hlsl"
    StaticCombo( S_ALPHA_TEST, F_ALPHA_TEST, Sys( ALL ) );
    RenderState( CullMode, NONE );

    float4 SamplePanel(float index,float u,float worldZ)
    {
        float4 rect=index<.5 ? g_vAtlasRect0 : (index<1.5 ? g_vAtlasRect1 : g_vAtlasRect2);
        float bottom=index<.5 ? g_flBottom0 : (index<1.5 ? g_flBottom1 : g_flBottom2);
        float row=rect.w-(worldZ-bottom)/g_flPixelScale;
        if(row<rect.y || row>rect.w) return float4(0,0,0,0);
        float2 uv=float2(lerp(rect.x,rect.z,u)/g_flAtlasWidth,1-row/g_flAtlasHeight);
        return g_tVista.Sample(VistaSampler,uv);
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init(i);
        float u = saturate((i.vTextureCoords.x-g_flImageU0)/(g_flImageU1-g_flImageU0));
        float4 vista=SamplePanel(g_flSector,u,m.WorldPosition.z);
        float neighbor=g_flSector,weight=0;
        if(u<.08 && g_flSector>.5) { neighbor=g_flSector-1; weight=.5*(1-smoothstep(0.0,.08,u)); }
        if(u>.92 && g_flSector<1.5) { neighbor=g_flSector+1; weight=.5*smoothstep(.92,1.0,u); }
        if(weight>0)
        {
            // Blend samples on this opaque surface, not layered transparent
            // geometry: both sides of a join evaluate the same boundary color.
            float4 other=SamplePanel(neighbor,1-u,m.WorldPosition.z);
            float alpha=lerp(vista.a,other.a,weight);
            vista.rgb=lerp(vista.rgb*vista.a,other.rgb*other.a,weight)/max(alpha,.0001);
            vista.a=alpha;
        }
        float coast = g_flCoastSide < -.5 ? u : 1-u;
        // The two outer ends descend to the water without stretching the image.
        float limit = lerp(-500.0,3500.0,smoothstep(0.0,.12,coast));
        float coastalCoverage = abs(g_flCoastSide)>.5 ? 1-smoothstep(limit-8,limit+8,m.WorldPosition.z) : 1;
        m.Opacity = vista.a*coastalCoverage;
        AdjustAlphaToCoverage(m);
        m.Albedo = vista.rgb*g_flVistaBrightness;
        m.Normal = float3(0,0,1);
        m.GeometricNormal = m.Normal;
        m.Roughness = 1;
        m.Metalness = 0;
        CombinerInput combiner = ShadingModelStandard::MaterialToCombinerInput(m);
        LightingTerms_t lighting = InitLightingTerms();
        ComputeDirectLighting(lighting,combiner);
        CalculateIndirectLighting(lighting,combiner);
        float3 color = (lighting.vDiffuse.rgb+lighting.vIndirectDiffuse.rgb)*combiner.vDiffuseColor.rgb;
        if (DepthNormals::WantsDepthNormals()) return DepthNormals::Output(m.Normal,m.Roughness,m.Opacity);
        return DoAtmospherics(m.WorldPosition,m.ScreenPosition.xy,float4(color,m.Opacity));
    }
}
