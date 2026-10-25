HEADER
{
    Description = "Forest Base world-projected wet cliff infill";
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
    SamplerState RockSampler < Filter(ANISO); AddressU(WRAP); AddressV(WRAP); MaxAniso(8); >;
    float RockMappingScale < Default(106); Range(16,512); UiGroup("Rock"); >;
    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::Init(i);
        {
            // Scan UVs remain untouched. Infill is projected on three world
            // planes so deep returns cannot stretch front-facing UVs into bars.
            float3 p=m.WorldPosition/RockMappingScale;
            float3 n=normalize(i.vNormalWs);
            // Infill has steep depth returns between scan patches. Its smooth
            // vertex normals can point forward even on a side-facing triangle;
            // use the actual surface derivatives for projection weights.
            float3 face=cross(ddx(m.WorldPosition),ddy(m.WorldPosition));
            face=dot(face,face)>.000001?normalize(face):n;
            float3 weights=pow(abs(face),4);
            weights/=max(dot(weights,float3(1,1,1)),.0001);
            float2 ux=p.yz,uy=p.xz,uz=p.xy;
            m.Albedo=(g_tColor.Sample(RockSampler,ux).rgb*weights.x+
                      g_tColor.Sample(RockSampler,uy).rgb*weights.y+
                      g_tColor.Sample(RockSampler,uz).rgb*weights.z)*g_flTintColor;
            float3 rma=g_tRma.Sample(RockSampler,ux).rgb*weights.x+
                       g_tRma.Sample(RockSampler,uy).rgb*weights.y+
                       g_tRma.Sample(RockSampler,uz).rgb*weights.z;
            m.Roughness=rma.r;
            m.AmbientOcclusion=rma.b;
            float3 a=DecodeNormal(g_tNormal.Sample(RockSampler,ux).rgb);
            float3 b=DecodeNormal(g_tNormal.Sample(RockSampler,uy).rgb);
            float3 c=DecodeNormal(g_tNormal.Sample(RockSampler,uz).rgb);
            float3 nx=float3(a.z*n.x,a.x+n.y,a.y+n.z);
            float3 ny=float3(b.x+n.x,b.z*n.y,b.y+n.z);
            float3 nz=float3(c.x+n.x,c.y+n.y,c.z*n.z);
            m.Normal=normalize(nx*weights.x+ny*weights.y+nz*weights.z);
        }
        float e=-m.WorldPosition.y,z=m.WorldPosition.z;
        float veins=sin(e*.031+sin(z*.007)*2)*sin(e*.012+z*.004);
        float wet=saturate(.35+.22*veins+.45*exp(-pow((e-430)/450,2)));
        m.Albedo*=lerp(float3(.63,.66,.68),float3(.38,.43,.45),wet);
        m.Roughness=clamp(m.Roughness*lerp(1,.60,wet),.24,.92);
        m.Metalness=0;
        return ShadingModelStandard::Shade(i,m);
    }
}
