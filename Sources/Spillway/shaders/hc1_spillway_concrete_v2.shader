HEADER
{
    Description = "Spillway weathered concrete: cast seams, rain streaks, damp foundations and wet terraces";
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
    float g_flWearScale < Default( 1 ); Range( .1, 8 ); >;
    float SWHash( float2 cell )
    {
        // Integer lattice corners must agree from either side of a noise cell.
        // A large sine hash loses that agreement after GPU floating-point
        // reassociation, exposing square steps in the wetness and reflections.
        uint2 q = asuint( int2( cell ) );
        uint h = q.x * 0x8DA6B343u ^ q.y * 0xD8163841u;
        h ^= h >> 15;
        h *= 0x2C1B3C6Du;
        h ^= h >> 12;
        h *= 0x297A2D39u;
        h ^= h >> 15;
        return float( h & 0x00FFFFFFu ) * ( 1.0 / 16777216.0 );
    }
    float SWN( float2 p )
    {
        float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(SWHash(a),SWHash(a+float2(1,0)),f.x),
                    lerp(SWHash(a+float2(0,1)),SWHash(a+1),f.x),f.y);
    }
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m=Material::From(i);
        m.Metalness=0;m.Transmission=0;
        float3 p=m.WorldPosition;
        float along=abs(i.vNormalWs.x)>.65 ? p.y : p.x;
        float2 wall=float2(along,p.z)/g_flWearScale;
        float macro=SWN(wall/float2(240,190));
        float rain=SWN(wall/float2(34,185)+11.3)*.7+SWN(wall/float2(9,60)+39)*.3;
        float vertical=1-smoothstep(.35,.9,abs(i.vNormalWs.z));
        float deposit=smoothstep(.34,.79,rain)*vertical;
        float base=(1-smoothstep(-190,45+macro*90,p.z))*vertical;
        m.Albedo*=lerp(.77,1.04,macro)*(1-deposit*.34);
        m.Albedo*=lerp(float3(1,1,1),float3(.38,.43,.34),base*.8);
        float2 panel=frac(wall/float2(192,160));
        float seam=1-smoothstep(.002,.008,min(min(panel.x,1-panel.x),min(panel.y,1-panel.y)));
        m.Albedo*=1-seam*vertical*.36;
        m.Roughness=clamp(m.Roughness+deposit*.15,.38,.94);
        if(i.vNormalWs.z>.9)
        {
            float patch=SWN(p.xy/180)*.65+SWN(p.xy/37+2.4)*.35;
            float wet=smoothstep(.43,.65,patch);
            m.Albedo*=lerp(.89,.60,wet);
            m.Roughness=lerp(.68,.12,wet);
            m.Normal=normalize(lerp(m.Normal,i.vNormalWs,wet*.78));
        }
        return ShadingModelStandard::Shade(i,m);
    }
}
