HEADER
{
    Description = "Spillway gravity-driven sheets, turbulent whitewater and spray";
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
    #define S_TRANSLUCENT 1
    #include "common/shared.hlsl"
}
struct VertexInput {
    #include "common/vertexinput.hlsl"
};
struct PixelInput {
    #include "common/pixelinput.hlsl"
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs(VertexInput i) { return FinalizeVertex(ProcessVertex(i)); }
}
PS
{
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"
    BoolAttribute(DoNotCastShadows,true);
    RenderState(DepthWriteEnable,false);
    RenderState(DepthEnable,true);
    RenderState(BlendEnable,true);
    RenderState(SrcBlend,SRC_ALPHA);
    RenderState(DstBlend,INV_SRC_ALPHA);
    RenderState(CullMode,NONE);
    float g_flFoam < Default(0); Range(0,2); >;
    float Hash(float2 p)
    {
        p-=floor(p/64)*64;
        float3 q=frac(p.xyx*.1031);
        q+=dot(q,q.yzx+33.33);
        return frac((q.x+q.y)*q.z);
    }
    float Noise(float2 p)
    {
        float2 a=floor(p),f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(Hash(a),Hash(a+float2(1,0)),f.x),lerp(Hash(a+float2(0,1)),Hash(a+1),f.x),f.y);
    }
    float Fractal(float2 p) { return Noise(p)*.57+Noise(p*2+3.1)*.28+Noise(p*4+17.7)*.15; }
    // Wrap each phase before adding position, preserving fractional precision
    // throughout long editor/game sessions. Integer octaves repeat seamlessly.
    float FallingZ(float z,float scale,float t) { return z/scale+frac(t*(610/scale)/64)*64; }
    float4 MainPs(PixelInput i):SV_Target0
    {
        Material m=Material::Init(i);
        float3 world=m.WorldPosition;
        float2 uv=i.vTextureCoords.xy;
        // z + speed*time makes every phase travel toward decreasing WORLD z.
        // The OBJ importer flips V; world-space gravity is independent of its convention.
        float t=g_flTime;
        float2 falling=float2(world.y/36,FallingZ(world.z,240,t));
        float warp=Fractal(float2(world.y/170,FallingZ(world.z,640,t)));
        float sheet=Fractal(falling+float2((warp-.5)*1.7,0));
        float thread=Noise(float2(world.y/11,FallingZ(world.z,165,t)));
        float spray=smoothstep(.30,.73,sheet*.8+thread*.2);
        float edge=smoothstep(0,.045,uv.x)*smoothstep(0,.045,1-uv.x);
        float broken=Fractal(float2(world.y/62,FallingZ(world.z,85,t)));
        m.Albedo=lerp(float3(.075,.115,.135),float3(.60,.65,.66),spray);
        m.Normal=normalize(i.vNormalWs+float3((sheet-.5)*.10,(thread-.5)*.08,0));
        m.Roughness=lerp(.16,.52,spray);
        m.Metalness=0; m.AmbientOcclusion=1;
        m.Emission=m.Albedo*.025;
        m.Opacity=edge*lerp(.76,.97,spray)*lerp(.88,1,broken);
        if(g_flFoam>.5)
        {
            // Tailrace moves south: plan -north is world -X.
            float2 p=(world.xy-float2(-145,0)*t)/float2(175,115);
            float curl=Fractal(p*.36);
            float f=Fractal(p+float2(curl*3,Noise(p*.63+4)*2));
            float foam=smoothstep(.46,.69,f);
            float2 q=(uv-.5)*2;
            float rim=saturate(1-dot(q,q));
            m.Albedo=float3(.49,.56,.58); m.Emission=m.Albedo*.025;
            m.Roughness=.57; m.Opacity=foam*rim*.72;
        }
        if(g_flFoam>1.5)
        {
            float2 q=(uv-.5)*2;
            float cloud=Fractal(uv*5+float2(t*.035,-t*.045));
            float rim=saturate(1-dot(q,q));
            m.Albedo=float3(.48,.54,.58); m.Emission=m.Albedo*.06;
            m.Opacity=rim*rim*smoothstep(.2,.65,cloud)*.20;
            m.Roughness=1;
        }
        return ShadingModelStandard::Shade(i,m);
    }
}
