HEADER
{
    Description = "M4 coated optical glass and collimated reticle";
    Version = 8;
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
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    RenderState( BlendEnable, true );
    // Premultiplied: the glass dims what's behind it by its alpha and adds what it reflects and the reticle's light.
    RenderState( SrcBlend, ONE );
    RenderState( DstBlend, INV_SRC_ALPHA );
    RenderState( BlendOp, ADD );
    RenderState( SrcBlendAlpha, ONE );
    RenderState( DstBlendAlpha, INV_SRC_ALPHA );
    RenderState( BlendOpAlpha, ADD );
    RenderState( DepthEnable, true );
    RenderState( DepthFunc, GREATER_EQUAL );
    RenderState( DepthWriteEnable, false );
    RenderState( CullMode, NONE );

    float3 g_vSightLightColor < UiType(Color); Default3(1.0,0.03,0.01); UiGroup("Reticle,10/10"); >;
    float g_flScopeReticle < Default(0.0); Range(0.0,1.0); UiGroup("Reticle,10/20"); >;
    float g_flUseReticleTexture < Default(0.0); Range(0.0,1.0); UiGroup("Reticle,10/30"); >;
    float g_flSightDistanceScale < Default(0.35); Range(0.0,20.0); UiGroup("Reticle,10/40"); >;
    // Opt-in: magnified sights still use their original clear reticle-only surface.
    // What a reflex or holographic window takes out of the view at normal incidence (its coatings' reflection and
    // absorption): ~0.06, so ~94% passes. It never writes depth.
    float g_flLensCoatingOpacity < Default(0.0); Range(0.0,0.4); UiGroup("Glass,10/10"); >;
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
        // The reticle-only path stays pixel-identical for scopes without a glass coating.
        if (g_flLensCoatingOpacity < 0.001)
        {
            clip(mark - 0.001);
            return float4(g_vSightLightColor * 1.4 * mark, mark);
        }

        // A reflex or holographic sight's window, from the shooter's side. It passes the view in grey (about 94%), and
        // reflects what's behind the shooter: weakly across the spectrum, its faces anti-reflection coated (~1.5%), and
        // strongly in the narrow red band its mirror coating returns for the dot, so reflections in it look faintly
        // red-pink. Everything it adds is reflected scene light; it has no colour of its own to lay over the view.
        // The objective is lightly curved: curve the shading normal, not the transmitted image or the aiming mark.
        float2 lensUv = saturate(i.vTextureCoords.xy);
        float2 fromCentre = (lensUv - 0.5) * 2.0;
        float3 towardEye = -viewRay;
        float3 facingNormal = dot(normal, towardEye) >= 0.0 ? normal : -normal;
        float3 curvedNormal = normalize(facingNormal +
            0.14 * (fromCentre.x * normalize(i.vTangentUWs) + fromCentre.y * normalize(i.vTangentVWs)));
        float ndotv = saturate(dot(curvedNormal, towardEye));
        float grazing = pow(1.0 - ndotv, 5.0);

        Material lens = Material::Init(i);
        lens.Normal = curvedNormal;
        lens.Metalness = 0.0;
        lens.Roughness = 0.04;
        lens.Albedo = 0.0;
        lens.Emission = 0.0;
        lens.Opacity = 1.0;
        lens.AmbientOcclusion = 1.0;
        lens.Transmission = 0.0;
        // Shade() reflects with an uncoated dielectric's 4% (Schlick); the coatings replace that reflectance.
        float3 reflection = max(ShadingModelStandard::Shade(i, lens).rgb, 0.0);
        // A sight inches from the eye reflects the shooter back at them: anywhere within ~35 degrees of the line back
        // to the eye it shows their own face in the hood's shade, not the room that the environment light holds.
        float backToEye = dot(reflect(viewRay, curvedNormal), towardEye);
        reflection *= lerp(1.0, 0.08, smoothstep(0.57, 0.82, backToEye));
        float coatingScale = g_flLensCoatingOpacity / 0.06;
        float3 coating = float3(0.035, 0.012, 0.014) * coatingScale;
        float3 reflectance = coating + (1.0 - coating) * grazing;
        float3 reflected = reflection * reflectance / (0.04 + 0.96 * grazing);

        // What it takes out of the view: the coatings' share, and more at a slant as both faces reflect more.
        float alpha = saturate(1.0 - (1.0 - g_flLensCoatingOpacity) * (1.0 - grazing) * (1.0 - grazing));
        // The dot is light the coating reflects to the eye: it adds to the view rather than covering it.
        float3 colour = reflected + g_vSightLightColor * 1.4 * saturate(mark);
        return float4(colour, alpha);
    }
}
