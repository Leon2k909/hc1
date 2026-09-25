HEADER
{
    Description = "M4 clear optic lens and collimated reticle";
    Version = 6;
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
    #define BLEND_MODE_ALREADY_SET 1
    #define DEPTH_STATE_ALREADY_SET 1
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
    PixelInput MainVs( VertexInput i )
    {
        return FinalizeVertex(ProcessVertex(i));
    }
}
PS
{
    #include "common/pixel.hlsl"
    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( BlendOp, ADD );
    RenderState( SrcBlendAlpha, ONE );
    RenderState( DstBlendAlpha, INV_SRC_ALPHA );
    RenderState( BlendOpAlpha, ADD );
    RenderState( DepthEnable, true );
    RenderState( DepthFunc, GREATER_EQUAL );
    RenderState( DepthWriteEnable, false );
    RenderState( CullMode, NONE );
    BoolAttribute( DoNotCastShadows, true );

    float3 g_vSightLightColor < UiType(Color); Default3(1.0,0.03,0.01); UiGroup("Reticle,10/10"); >;
    float g_flScopeReticle < Default(0.0); Range(0.0,1.0); UiGroup("Reticle,10/20"); >;
    float g_flUseReticleTexture < Default(0.0); Range(0.0,1.0); UiGroup("Reticle,10/30"); >;
    float g_flSightDistanceScale < Default(0.35); Range(0.0,20.0); UiGroup("Reticle,10/40"); >;
    // Scale, rotation and position are set per weapon by the gunsmith.
    float g_flReticleScale < Default(1.0); Range(0.1,10.0); UiGroup("Reticle,10/45"); >;
    float g_flReticleRotation < Default(0.0); Range(-180.0,180.0); UiGroup("Reticle,10/46"); >;
    float2 g_vReticleOffset < Default2(0.0,0.0); Range2(-0.08,-0.08,0.08,0.08); UiGroup("Reticle,10/47"); >;
    CreateInputTexture2D( RedDot, Linear, 8, "", "_color", "Reticle,10/50", Default3(0.0,0.0,0.0) );
    Texture2D g_tRedDot < Channel(R,Box(RedDot),Linear); OutputFormat(BC7); SrgbRead(false); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float3 viewRay = normalize(i.vPositionWithOffsetWs.xyz);
        float3 normal = normalize(i.vNormalWs);
        float denominator = dot(viewRay,normal);
        denominator = abs(denominator)<0.01 ? 0.01 : denominator;
        float project = -g_flSightDistanceScale / denominator;
        float2 uv = i.vTextureCoords.xy + project * 0.5 * float2(dot(viewRay,i.vTangentUWs),dot(viewRay,i.vTangentVWs));
        float2 centred = uv - 0.5 - g_vReticleOffset;
        float angle = g_flReticleRotation * 0.01745329252;
        float sine, cosine;
        sincos(angle, sine, cosine);
        uv = float2(cosine * centred.x + sine * centred.y, -sine * centred.x + cosine * centred.y)
            / max(g_flReticleScale, 0.01) + 0.5;
        float2 p = uv - 0.5;
        float aa = max(max(fwidth(p.x),fwidth(p.y)),0.0008);
        float mark = 1.0-smoothstep(0.010,0.010+aa,length(p));
        if ( g_flScopeReticle > 0.5 )
        {
            float lineX = 1.0-smoothstep(0.002,0.002+aa,abs(p.x));
            float lineY = 1.0-smoothstep(0.002,0.002+aa,abs(p.y));
            float gap = smoothstep(0.015,0.020,max(abs(p.x),abs(p.y)));
            float ticks = abs(frac(abs(p.y)/0.065+0.5)-0.5)*0.065;
            ticks = (1.0-smoothstep(0.002,0.002+aa,ticks))*(1.0-smoothstep(0.016,0.020,abs(p.x)))*step(0.05,abs(p.y));
            mark = max(mark,max(max(lineX,lineY)*gap,ticks))*(1.0-smoothstep(0.30,0.34,length(p)));
        }
        if ( g_flUseReticleTexture > 0.5 )
            mark = g_tRedDot.Sample(g_sAniso,uv).r * step(0.0,uv.x)*step(uv.x,1.0)*step(0.0,uv.y)*step(uv.y,1.0);
        // Empty lens pixels must leave both scene colour and overlay coverage untouched.
        clip(mark - 0.001);
        return float4(g_vSightLightColor*1.4,mark);
    }
}
