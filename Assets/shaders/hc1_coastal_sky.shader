// Lowtide: a fixed HDR sky and sun, with two moving cloud layers.
// Cloud lighting/opacity is authored offline (Tools/lowtide_sky.py). Only three
// sky texture reads per visible sky pixel: no runtime volume march, meshes or particles.
HEADER
{
    Description = "Coastal sky with wind-driven, shaded clouds";
    Version = 1;
}

MODES
{
    Forward();
}

FEATURES
{
    #include "vr_common_features.fxc"
}

COMMON
{
    #include "system.fxc"
    #include "vr_common.fxc"
}

struct VS_INPUT
{
    float4 vPositionOs : POSITION < Semantic( PosXyz ); >;
};

struct PS_INPUT
{
    float3 vRay : TEXCOORD1;
    #if ( PROGRAM == VFX_PROGRAM_VS )
        float4 vPositionPs : SV_Position;
    #endif
    #if ( PROGRAM == VFX_PROGRAM_PS )
        float4 vPositionSs : SV_Position;
    #endif
};

VS
{
    PS_INPUT MainVs( VS_INPUT i )
    {
        PS_INPUT o;
        float3 position = g_vCameraPositionWs.xyz + i.vPositionOs.xyz * (g_flNearPlane + g_flFarPlane);
        o.vPositionPs = Position3WsToPs(position);
        o.vRay = i.vPositionOs.xyz;
        return o;
    }
}

PS
{
    #include "volumetric_fog.fxc"

    RenderState( CullMode, NONE );
    RenderState( DepthWriteEnable, false );
    RenderState( DepthEnable, true );
    RenderState( DepthFunc, GREATER_EQUAL );
    BoolAttribute( sky, true );

    CreateInputTextureCube( SkyTexture, Linear, 16, "", "_sky", "Sky,10/10", Default3(0.1, 0.2, 0.4) );
    TextureCube g_tSkyTexture < Channel( RGB, Box(SkyTexture), Linear ); OutputFormat( BC6H ); SrgbRead( false ); >;
    CreateInputTexture2D( Clouds, Srgb, 8, "", "_clouds", "Clouds,20/10", Default4(0, 0, 0, 0) );
    Texture2D g_tClouds < Channel( RGBA, Box(Clouds), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    CreateInputTexture2D( HighClouds, Linear, 8, "", "_highclouds", "Clouds,20/20", Default(0) );
    Texture2D g_tHighClouds < Channel( R, Box(HighClouds), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState g_sClouds < Filter( ANISO ); AddressU( WRAP ); AddressV( WRAP ); >;
    SamplerState g_sSky < Filter( TRILINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;

    float g_flCloudAltitude < Default(1550); Range(500, 5000); UiGroup("Clouds,20/30"); >;
    float g_flCloudTile < Default(8000); Range(2000, 30000); UiGroup("Clouds,20/40"); >;
    float4 g_vCloudWind < Default4(7.8, -10.4, 0, 0); UiGroup("Clouds,20/50"); >;
    float g_flCloudRadiance < Default(0.7); Range(0.1, 4); UiGroup("Clouds,20/60"); >;
    float g_flSkyCloudTime < Default(0); >;
    float g_flCloudDensity < Default(1); >;
    float g_flWeatherOvercast < Default(0); >;
    // QA can compare fixed times using a copied material; the map leaves this zero.
    float g_flCloudTimeOffset < Default(0); UiGroup("Clouds,20/70"); >;

    float4 MainPs( PS_INPUT i ) : SV_Target0
    {
        // SkyBox2D renders a fullscreen primitive. Reconstruct the world ray from
        // the camera projection; its mesh coordinates are not a world-space dome.
        float2 uvScreen = CalculateViewportUv(i.vPositionSs.xy);
        float2 clip = float2(uvScreen.x * 2 - 1, 1 - uvScreen.y * 2);
        float3 ray = normalize(mul(g_matProjectionToWorld, float4(clip, 0.00001, 1)).xyz);
        float3 sky = g_tSkyTexture.Sample(g_sSky, ray).rgb;
        // Perspective on a horizontal layer, with the distant banks dissolving into
        // coastal haze. Clamp/fade before the horizon to avoid infinite UV derivatives.
        float2 layer = ray.xy / max(ray.z, 0.055);
        float horizon = smoothstep(0.055, 0.19, ray.z);
        float time = g_flSkyCloudTime + g_flCloudTimeOffset;
        // A negative UV translation moves actual cloud features WITH the wind.
        // frac keeps precision after long editor/game sessions; the textures tile.
        float2 drift = frac(g_vCloudWind.xy * (time / g_flCloudTile));
        float2 plane = layer * (g_flCloudAltitude / g_flCloudTile) - drift;
        // Align the source's upper-left illumination with Lowtide's south-west sun.
        float2 uv = float2(0.5 * plane.x - 0.8660254 * plane.y, 0.8660254 * plane.x + 0.5 * plane.y) + float2(0.37, 0.61);
        float high = g_tHighClouds.Sample(g_sClouds, layer * 0.34 - drift * 0.65).r;
        sky = lerp(sky, float3(0.62, 0.69, 0.78), saturate(high * g_flCloudDensity) * horizon * 0.24);
        float4 cloud = g_tClouds.Sample(g_sClouds, uv);
        sky = lerp(sky, cloud.rgb * g_flCloudRadiance, saturate(cloud.a * g_flCloudDensity) * horizon);
        // A front thickens into a softly textured grey deck over minutes, without
        // replacing the moving sky at a threshold halfway through the transition.
        float3 overcast = lerp(float3(0.224, 0.231, 0.244), float3(0.375, 0.391, 0.417), saturate(ray.z));
        overcast *= 1 + (high - 0.5) * 0.03 + (cloud.a - 0.5) * 0.06;
        sky = lerp(sky, overcast, saturate(g_flWeatherOvercast));
        // Keep the sky compatible with the map's volumetric atmosphere.
        float3 farPosition = g_vCameraPositionWs.xyz + ray * g_flFarPlane;
        return float4(ApplyVolumetricFog(sky, farPosition, i.vPositionSs.xy), 1);
    }
}
