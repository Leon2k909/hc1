HEADER
{
    Description = "Spillway: turbulent falling water, soft banks and advected whitewater";
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
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
    #include "common/pixel.hlsl"
    BoolAttribute( DoNotCastShadows, true );
    RenderState( DepthWriteEnable, false );
    RenderState( DepthEnable, true );
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( CullMode, NONE );
    float g_flFoam < Default( 0 ); Range( 0, 2 ); UiGroup( "Flow" ); >;

    float Hash( float2 p ) { return frac( sin( dot( p, float2( 127.1, 311.7 ) ) ) * 43758.5453 ); }
    float Noise( float2 p )
    {
        float2 a = floor( p ), f = frac( p ); f = f * f * ( 3 - 2 * f );
        return lerp( lerp( Hash( a ), Hash( a + float2(1,0) ), f.x ),
                     lerp( Hash( a + float2(0,1) ), Hash( a + 1 ), f.x ), f.y );
    }
    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::Init( i );
        float2 uv = i.vTextureCoords.xy;
        float t = g_flTime;
        float2 p = float2( uv.x * 28, uv.y * 3 - t * 2.4 );
        float noise = Noise( p ) * .55 + Noise( p * 2.1 + float2(1,t*.6) ) * .3 + Noise( p * 4.7 ) * .15;
        float streak = Noise( float2( uv.x * 83, uv.y * 1.7 - t * 1.6 ) );
        float edge = smoothstep( 0, .08, uv.x ) * smoothstep( 0, .08, 1 - uv.x );
        float foam = smoothstep( .25, .76, noise + streak * .24 );
        if ( g_flFoam > .5 )
        {
            p = uv * float2(12,18) + float2(0,-t*2.0);
            noise = Noise( p + Noise( p*.38 )*3 ) * .7 + Noise( p * 2.3 ) * .3;
            foam = smoothstep( .43, .68, noise );
            edge *= smoothstep(0,.13,uv.y) * smoothstep(0,.23,1-uv.y);
        }
        m.Albedo = lerp( float3(.30,.39,.43), float3(.66,.73,.77), foam );
        m.Normal = normalize( i.vNormalWs + float3( (noise-.5)*.18, 0, (streak-.5)*.12 ) );
        m.Roughness = lerp( .17, .53, foam ); m.Metalness = 0; m.AmbientOcclusion = 1;
        m.Emission = m.Albedo * .12;
        m.Opacity = edge * (g_flFoam > .5 ? foam * .87 : .72 + foam*.25);
        if (g_flFoam > 1.5)
        {
            float2 q=(uv-.5)*2;
            float cloud=Noise(uv*4+float2(t*.06,0))*.65+Noise(uv*9-float2(0,t*.03))*.35;
            float rim=saturate(1-dot(q,q));
            m.Albedo=float3(.63,.70,.74);m.Emission=m.Albedo*.2;
            m.Opacity=rim*rim*smoothstep(.15,.60,cloud)*.25;
            m.Roughness=1;
        }
        return ShadingModelStandard::Shade( i, m );
    }
}
