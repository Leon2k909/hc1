HEADER
{
    Description = "Forest Base scanned asphalt with world-space rain saturation";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth(S_MODE_DEPTH);
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
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float RainHash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float RainNoise(float2 p)
    {
        float2 a=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(RainHash(a),RainHash(a+float2(1,0)),f.x),
                    lerp(RainHash(a+float2(0,1)),RainHash(a+1),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 p=m.WorldPosition.xy;
        float rain=RainNoise(p*.0031)*.65+RainNoise(p*.0087+17)*.35;
        // Local shallow pools, separated by damp aggregate.
        float wet=smoothstep(.43,.68,rain);
        m.Albedo*=lerp(.86,.46,wet);
        m.Roughness=lerp(max(.52,m.Roughness),.055,wet);
        // A rain film levels the aggregate normal; retaining most of the
        // asphalt bump broke broad puddle reflections into dry-looking grains.
        m.Normal=normalize(lerp(m.Normal,i.vNormalWs,wet*.94));
        m.Metalness=0;
        return ShadingModelStandard::Shade(i,m);
    }
}
