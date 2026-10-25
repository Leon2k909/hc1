HEADER
{
    Description = "Forest Base scanned mud with soft irregular track edges";
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
    PixelInput MainVs(VertexInput i) { return FinalizeVertex(ProcessVertex(i)); }
}
PS
{
    #define S_TRANSLUCENT 1
    #define BLEND_MODE_ALREADY_SET 1
    RenderState(BlendEnable, true);
    RenderState(SrcBlend, SRC_ALPHA);
    RenderState(DstBlend, INV_SRC_ALPHA);
    RenderState(DepthWriteEnable, false);
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float MudHash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float MudNoise(float2 p)
    {
        float2 a=floor(p),f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(MudHash(a),MudHash(a+float2(1,0)),f.x),
                    lerp(MudHash(a+float2(0,1)),MudHash(a+1),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        float across=i.vTextureCoords.x;
        PixelInput tiled=i;
        tiled.vTextureCoords.x*=1.6;
        Material m=Material::From(tiled);
        float noise=MudNoise(m.WorldPosition.xy*.055);
        float edge=min(across,1-across);
        m.Opacity=smoothstep(.025+noise*.025,.15+noise*.14,edge)*lerp(.55,.94,noise);
        m.Roughness=clamp(m.Roughness*.85,.14,.80);
        m.Metalness=0;
        return ShadingModelStandard::Shade(i,m);
    }
}
