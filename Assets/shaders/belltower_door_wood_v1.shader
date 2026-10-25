HEADER
{
    Description = "Belltower panelled doors: photographed timber at joinery scale";
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

    float g_flDoorNormal < Default( .16 ); Range( 0, .5 ); >;
    float g_flDoorRoughnessScale < Default( .68 ); Range( .4, 1 ); >;
    float g_flDoorAo < Default( .18 ); Range( 0, 1 ); >;

    // Insets within the original scan's nine boards, excluding photographed joints.
    static const float2 DoorBoardStrips[9] = {
        float2(.012,.108),float2(.132,.226),float2(.248,.335),
        float2(.360,.442),float2(.471,.552),float2(.580,.647),
        float2(.676,.753),float2(.786,.873),float2(.903,.981)
    };

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        #if !S_MODE_DEPTH
        // The existing geometry carries a 48 x 94 inch atlas, with texture V down.
        float2 p = float2(saturate(i.vTextureCoords.x)*48, (1-saturate(i.vTextureCoords.y))*94);
        float2 px = ddx(p), py = ddy(p);
        float leaf = min(floor(p.x/24),1);
        float x = p.x-leaf*24;
        bool rail = x>=4 && x<=20 && (p.y<9 || (p.y>36 && p.y<44) || p.y>89);
        float across, along, part;
        float2 gradientX, gradientY;
        if (rail)
        {
            float bottom = p.y<9 ? 0 : (p.y<44 ? 36 : 89);
            across = p.y-bottom;
            along = x-4;
            part = p.y<9 ? 4 : (p.y<44 ? 5 : 6);
            gradientX = px.yx;
            gradientY = py.yx;
        }
        else
        {
            across = x-(x>20 ? 20 : (x<4 ? 0 : 4));
            along = p.y;
            part = x<4 ? 0 : (x>20 ? 1 : (p.y<40 ? 2 : 3));
            gradientX = px;
            gradientY = py;
        }
        // Preserve fine grain scale on wide panels instead of enlarging one narrow board.
        float board = floor(across/3.5);
        float seed = leaf*17+part*5+board*3;
        int index = (int)fmod(seed,9);
        float2 strip = DoorBoardStrips[index];
        float crossScale = (strip.y-strip.x)*.94/3.5;
        float2 uv = float2(lerp(strip.x,strip.y,frac(across/3.5)*.94+.03),
                           along/(1000.0/25.4)+frac(seed*.173));
        float2 gx = gradientX*float2(crossScale,25.4/1000.0);
        float2 gy = gradientY*float2(crossScale,25.4/1000.0);
        // Explicit gradients avoid artificial blurry mips at timber-piece boundaries.
        float4 color = g_tColor.SampleGrad(TextureFiltering,uv,gx,gy);
        float4 normal = g_tNormal.SampleGrad(TextureFiltering,uv,gx,gy);
        float4 rma = g_tRma.SampleGrad(TextureFiltering,uv,gx,gy);
        m.Albedo = saturate(color.rgb*g_flTintColor*i.vVertexColor.rgb*
                           lerp(.97,1.03,frac(seed*.371)));
        float3 n = DecodeNormal(normal.xyz);
        n.xy = rail ? float2(n.y,-n.x) : float2(n.x,-n.y);
        n.xy *= g_flDoorNormal;
        m.Normal = TransformNormal(normalize(n),i.vNormalWs,i.vTangentUWs,i.vTangentVWs);
        m.Roughness = clamp(rma.r*g_flDoorRoughnessScale,.46,.76);
        m.AmbientOcclusion = lerp(1.0,rma.b,g_flDoorAo);
        m.TintMask = normal.a;
        m.TextureCoords = uv;
        #endif
        m.Metalness = 0;
        m.Transmission = 0;
        m.Opacity = 1;
        return ShadingModelStandard::Shade(i,m);
    }
}
