HEADER
{
    Description = "M4 coated optical glass and collimated reticle";
    Version = 9;
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
    // The optic model's own forward (x) and up (z) axes in world space: a red dot's reticle is collimated along them.
    float3 vOpticForwardWs : TEXCOORD8;
    float3 vOpticUpWs : TEXCOORD9;
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i )
    {
        PixelInput o = ProcessVertex( i );
        float3x4 m = GetTransformMatrix( i.nInstanceTransformID );
        o.vOpticForwardWs = float3( m[0][0], m[1][0], m[2][0] );
        o.vOpticUpWs = float3( m[0][2], m[1][2], m[2][2] );
        return FinalizeVertex( o );
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
    // A 1x sight's reticle in reticle units per radian off its axis: the dot (0.010 across its middle) is then 1.8 mrad
    // in radius, about what the old projection drew from the aimed eye.
    float g_flCollimationScale < Default(5.5); Range(1.0,40.0); UiGroup("Reticle,10/41"); >;
    // Opt-in: magnified sights still use their original clear reticle-only surface.
    // What a reflex or holographic window takes out of the view at normal incidence (its coatings' reflection and
    // absorption): ~0.06, so ~94% passes. It never writes depth.
    float g_flLensCoatingOpacity < Default(0.0); Range(0.0,0.4); UiGroup("Glass,10/10"); >;
    // What the window passes of each colour, against its brightest: the dot's mirror coating reflects a narrow red band
    // out of the view, so a reflex or holographic sight looks through slightly cyan.
    float3 g_vWindowTint < UiType(Color); Default3(1.0,1.0,1.0); UiGroup("Glass,10/20"); >;
    // How much dust and how many smudges are on the window (0 clean), and where they fall.
    float g_flDust < Default(0.0); Range(0.0,2.0); UiGroup("Glass,10/30"); >;
    float g_flDustSeed < Default(0.0); Range(0.0,100.0); UiGroup("Glass,10/40"); >;
    // How much of the room the window reflects where it would show the shooter's own face (within ~35 degrees of the
    // line back to the eye): the face is in the hood's shade, but it isn't black.
    float g_flFaceShade < Default(0.08); Range(0.0,1.0); UiGroup("Glass,10/50"); >;
    // An even share of the light falling on the window that its coatings and the film on handled glass scatter toward
    // the eye. It's lit by the scene, so it lifts the window over a dark background in the light and vanishes in the dark.
    float g_flHaze < Default(0.0); Range(0.0,0.1); UiGroup("Glass,10/60"); >;
    // The scene behind the window, for the share of its colour the tint takes out (as the engine's layered glass).
    BoolAttribute( bWantsFBCopyTexture, true );
    Texture2D g_tFrameBufferCopyTexture < Attribute( "FrameBufferCopyTexture" ); SrgbRead( false ); >;
    // Scale, rotation and position are set per weapon by the gunsmith.
    float g_flReticleScale < Default(1.0); Range(0.1,10.0); UiGroup("Reticle,10/45"); >;
    float g_flReticleRotation < Default(0.0); Range(-180.0,180.0); UiGroup("Reticle,10/46"); >;
    float2 g_vReticleOffset < Default2(0.0,0.0); Range2(-0.08,-0.08,0.08,0.08); UiGroup("Reticle,10/47"); >;
    CreateInputTexture2D( RedDot, Linear, 8, "", "_color", "Reticle,10/50", Default3(0.0,0.0,0.0) );
    Texture2D g_tRedDot < Channel(R,Box(RedDot),Linear); OutputFormat(BC7); SrgbRead(false); >;

    float Hash21( float2 p )
    {
        return frac( sin( dot( p, float2( 127.1, 311.7 ) ) ) * 43758.5453 );
    }

    float ValueNoise( float2 p )
    {
        float2 cell = floor( p );
        float2 f = frac( p );
        f = f * f * ( 3.0 - 2.0 * f );
        return lerp( lerp( Hash21( cell ), Hash21( cell + float2( 1, 0 ) ), f.x ),
                     lerp( Hash21( cell + float2( 0, 1 ) ), Hash21( cell + float2( 1, 1 ) ), f.x ), f.y );
    }

    // What share of the light through this point of the window dust and smudges scatter: specks of three sizes, about
    // one in a hundred cells, and the faint film fingers and rain leave in patches. The eye focuses past the window, so
    // a speck is a soft blur, never a sharp dot; its edge is still filtered across the pixel, so it doesn't flicker.
    float WindowScatter( float2 uv, float seed )
    {
        float scatter = 0.0;
        [unroll]
        for ( int layer = 0; layer < 3; layer++ )
        {
            float cells = layer == 0 ? 150.0 : ( layer == 1 ? 64.0 : 26.0 );
            float chance = layer == 0 ? 0.012 : ( layer == 1 ? 0.01 : 0.006 );
            float strength = layer == 0 ? 0.22 : ( layer == 1 ? 0.16 : 0.1 );
            float2 p = uv * cells + seed * ( 17.31 + layer * 29.7 );
            float2 cell = floor( p );
            float h = Hash21( cell + layer * 41.3 );
            float2 centre = 0.25 + 0.5 * float2( frac( h * 97.31 ), frac( h * 53.17 ) );
            float radius = 0.12 + 0.2 * frac( h * 13.7 );
            float d = length( frac( p ) - centre ) / radius;
            float aa = max( fwidth( d ), 0.001 );
            scatter += step( 1.0 - chance, frac( h * 7.13 ) ) * strength * ( 1.0 - smoothstep( 0.2, 1.0 + aa, d ) );
        }
        float film = ValueNoise( uv * 3.0 + seed ) * 0.6 + ValueNoise( uv * 7.0 - seed ) * 0.4;
        return scatter + 0.004 + 0.016 * smoothstep( 0.55, 0.85, film );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float3 viewRay = normalize(i.vPositionWithOffsetWs.xyz);
        float3 normal = normalize(i.vNormalWs);
        float2 uv;
        if ( g_flScopeReticle > 0.5 )
        {
            // The Scout 3x's crosshair, drawn a little behind its glass. The MWII magnified sights leave g_flScopeReticle
            // at 0, so their glass is collimated too; once raised, ScopeOverlay's lens picture covers it.
            float denominator = dot(viewRay,normal);
            denominator = abs(denominator)<0.01 ? 0.01 : denominator;
            float project = -g_flSightDistanceScale / denominator;
            uv = i.vTextureCoords.xy + project * 0.5 * float2(dot(viewRay,i.vTangentUWs),dot(viewRay,i.vTangentVWs));
        }
        else
        {
            // A reflex or holographic sight collimates its reticle at infinity, so where the dot shows depends only on
            // which way the eye looks through the window, against the way the sight points: never on where the eye is.
            // Moving the head moves the window round the dot, and the dot stays on what the sight points at.
            float3 forward = normalize(i.vOpticForwardWs);
            float3 up = normalize(i.vOpticUpWs);
            float3 side = cross(up, forward);
            float along = abs(dot(viewRay, forward));
            // The window's own texture axes say which way the reticle's art reads.
            float2 axes = float2(dot(i.vTangentUWs, side) < 0.0 ? -1.0 : 1.0, dot(i.vTangentVWs, up) < 0.0 ? -1.0 : 1.0);
            uv = 0.5 + g_flCollimationScale * axes * float2(dot(viewRay, side), dot(viewRay, up)) / max(along, 0.05);
        }
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
        reflection *= lerp(1.0, g_flFaceShade, smoothstep(0.57, 0.82, backToEye));
        float coatingScale = g_flLensCoatingOpacity / 0.06;
        float3 coating = float3(0.035, 0.012, 0.014) * coatingScale;
        float3 reflectance = coating + (1.0 - coating) * grazing;
        float3 reflected = reflection * reflectance / (0.04 + 0.96 * grazing);

        // What it passes of each colour: the coatings' share, tinted, and less at a slant as both faces reflect more.
        float3 transmission = (1.0 - g_flLensCoatingOpacity) * saturate(g_vWindowTint) * (1.0 - grazing) * (1.0 - grazing);
        float passed = min(transmission.x, min(transmission.y, transmission.z));

        // Dust and smudges scatter what lights the window toward the eye (lit by the scene, so they vanish in the
        // dark), and take that much out of the view behind.
        float scatter = saturate((g_flDust > 0.0 ? g_flDust * WindowScatter(lensUv, g_flDustSeed) : 0.0) + g_flHaze);
        float3 dustLight = 0.0;
        if (scatter > 0.0)
        {
            Material dust = Material::Init(i);
            dust.Normal = facingNormal;
            dust.Metalness = 0.0;
            dust.Roughness = 1.0;
            dust.Albedo = float3(0.62, 0.58, 0.52);
            dust.Emission = 0.0;
            dust.Opacity = 1.0;
            dust.AmbientOcclusion = 1.0;
            dust.Transmission = 0.0;
            dustLight = max(ShadingModelStandard::Shade(i, dust).rgb, 0.0) * scatter;
        }

        // The view passes at the dimmest colour's share through the blend; the colours it passes more of come from
        // the scene behind (the engine's layered glass does the same).
        float2 screenUv = CalculateViewportUv( i.vPositionSs.xy ) * g_vFrameBufferCopyInvSizeAndUvScale.zw;
        float3 behind = g_tFrameBufferCopyTexture.SampleLevel(g_sTrilinearClamp, screenUv, 0).rgb;
        float3 tinted = behind * (transmission - passed) * (1.0 - scatter);
        float alpha = saturate(1.0 - passed * (1.0 - scatter));
        // The dot is light the coating reflects to the eye: it adds to the view rather than covering it.
        float3 colour = reflected + tinted + dustLight + g_vSightLightColor * 1.4 * saturate(mark);
        return float4(colour, alpha);
    }
}
