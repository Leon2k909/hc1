HEADER
{
    Description = "Fine fired terracotta with continuous projection and restrained pot weathering";
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
    float g_flClayTileInches < Default( 12 ); Range( 4, 48 ); UiGroup( "Clay,20/10" ); >;
    float g_flClayNormalStrength < Default( .65 ); Range( 0, 1 ); UiGroup( "Clay,20/20" ); >;
    float g_flClayWeathering < Default( .7 ); Range( 0, 1 ); UiGroup( "Clay,20/30" ); >;

    float ClayHash( float2 p ) { return frac( sin( dot( p, float2( 127.1,311.7 ) ) ) * 43758.5453 ); }
    float ClayNoise( float2 p )
    {
        float2 a=floor(p),f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(ClayHash(a),ClayHash(a+float2(1,0)),f.x),
                    lerp(ClayHash(a+float2(0,1)),ClayHash(a+1),f.x),f.y);
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m=Material::Init(i);
        #if !S_MODE_DEPTH
        float3 p=m.WorldPosition;
        float3 n=normalize(i.vNormalWs);
        float3 w=pow(abs(n),6); w/=max(w.x+w.y+w.z,.0001);
        float2 ux=p.zy/g_flClayTileInches,uy=p.xz/g_flClayTileInches,uz=p.xy/g_flClayTileInches;
        float3 color=g_tColor.Sample(TextureFiltering,ux).rgb*w.x
                    +g_tColor.Sample(TextureFiltering,uy).rgb*w.y
                    +g_tColor.Sample(TextureFiltering,uz).rgb*w.z;
        float3 nx=DecodeNormal(g_tNormal.Sample(TextureFiltering,ux).xyz);
        float3 ny=DecodeNormal(g_tNormal.Sample(TextureFiltering,uy).xyz);
        float3 nz=DecodeNormal(g_tNormal.Sample(TextureFiltering,uz).xyz);
        float3 bump=float3(0,nx.y,nx.x)*w.x+float3(ny.x,0,ny.y)*w.y+float3(nz.x,nz.y,0)*w.z;
        bump-=n*dot(bump,n);
        float rough=g_tRma.Sample(TextureFiltering,ux).r*w.x
                   +g_tRma.Sample(TextureFiltering,uy).r*w.y
                   +g_tRma.Sample(TextureFiltering,uz).r*w.z;
        float2 area=float2(p.x+.31*p.y,p.z);
        float patch=.7*ClayNoise(area/3.5)+.3*ClayNoise(area/.64+9.4);
        float damp=(1-smoothstep(.35,4.3,p.z+1.8*(patch-.5)))*g_flClayWeathering;
        float rim=smoothstep(14.6,17.1,p.z)*(1-smoothstep(18.2,19,p.z));
        float salts=rim*smoothstep(.42,.72,patch)*.30*g_flClayWeathering;
        float luma=dot(color,float3(.2126,.7152,.0722));
        color=lerp(color,luma.xxx,.17)*g_flTintColor;
        color*=1-.22*damp;
        color=lerp(color,float3(.48,.43,.34),salts);
        m.Albedo=color*i.vVertexColor.rgb;
        m.Normal=normalize(n+bump*g_flClayNormalStrength);
        m.Roughness=clamp(rough-.10*damp+.05*salts,.66,.94);
        m.AmbientOcclusion=1;
        m.TextureCoords=uy;
        m.TintMask=1;
        #endif
        m.Metalness=0;
        m.Transmission=0;
        m.Opacity=1;
        return ShadingModelStandard::Shade(i,m);
    }
}
