HEADER
{
    Description = "Weathered bronze for the Veridant lion crown";
}
FEATURES
{
    #include "common/features.hlsl"
}
MODES
{
    Forward();
    Depth( S_MODE_DEPTH );
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
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/pixel.hlsl"

    float HashCell( float3 p )
    {
        p = frac(p * float3(.1031, .1099, .0973));
        p += dot(p, p.yzx + 19.19);
        return frac((p.x + p.y) * p.z);
    }

    float PatinaNoise( float3 p )
    {
        float3 cell = floor(p);
        float3 f = frac(p);
        f = f * f * (3 - 2 * f);
        float4 low = float4(HashCell(cell), HashCell(cell + float3(1, 0, 0)),
            HashCell(cell + float3(0, 1, 0)), HashCell(cell + float3(1, 1, 0)));
        cell.z += 1;
        float4 high = float4(HashCell(cell), HashCell(cell + float3(1, 0, 0)),
            HashCell(cell + float3(0, 1, 0)), HashCell(cell + float3(1, 1, 0)));
        float4 row = lerp(low, high, f.z);
        return lerp(lerp(row.x, row.y, f.x), lerp(row.z, row.w, f.x), f.y);
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init(i);
        float3 p = m.WorldPosition;
        float grainFade = 1 - smoothstep(.05, .24, length(fwidth(p)));
        float casting = PatinaNoise(p * 3.35) - .5;
        float mottling = PatinaNoise(p * .42) * .54 + PatinaNoise(p * 1.1 + 17) * .31
            + PatinaNoise(p * 2.8 + 31) * .15;
        float oxide = smoothstep(.40, .74, mottling);
        float3 normal = normalize(i.vNormalWs);
        float3 dx = ddx(p);
        float3 dy = ddy(p);
        float curvature = .5 * (dot(ddx(normal), dx) / max(.001, dot(dx, dx))
            + dot(ddy(normal), dy) / max(.001, dot(dy, dy)));
        float worn = smoothstep(.08, .55, curvature);
        float polish = (.45 * smoothstep(.08, .90, normal.z) + .55 * worn) * (1 - oxide);
        float3 copper = lerp(float3(.091, .078, .062), float3(.153, .129, .101), polish);
        m.Albedo = lerp(copper, float3(.053, .085, .075), oxide * .56) * (1 + casting * .13 * grainFade);
        m.Roughness = lerp(.62, .80, oxide) + casting * .055 * grainFade - worn * .055;
        m.Metalness = lerp(.43, .16, oxide);
        m.AmbientOcclusion = 1;
        m.Opacity = 1;
        m.Normal = normal;
        return ShadingModelStandard::Shade(i, m);
    }
}
