HEADER
{
    Description = "Forest Base vehicle surfaces with irregular lower-body road grime";
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
    float GrimeHash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float GrimeNoise(float2 p)
    {
        float2 a=floor(p),f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(GrimeHash(a),GrimeHash(a+float2(1,0)),f.x),
                    lerp(GrimeHash(a+float2(0,1)),GrimeHash(a+1),f.x),f.y);
    }
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float3 p=m.WorldPosition;
        // These parked vehicles are authored at compound grade z=0. Road
        // spray varies across the body instead of a straight horizontal band.
        float noise=GrimeNoise(p.xy*.059+p.z*.031);
        float fleck=GrimeNoise(p.xy*.33+p.z*.18);
        float dirt=(1-smoothstep(19,66,p.z+noise*19))*(.25+.75*noise);
        dirt=saturate(dirt+step(.82,fleck)*(1-smoothstep(30,82,p.z))*.12);
        m.Albedo=lerp(m.Albedo,m.Albedo*.50+float3(.035,.022,.012),dirt*.68);
        m.Roughness=lerp(m.Roughness,.86,dirt*.85);
        m.Metalness*=1-dirt;
        return ShadingModelStandard::Shade(i,m);
    }
}
