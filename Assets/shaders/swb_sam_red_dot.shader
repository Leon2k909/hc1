HEADER
{
    Description = "Red Dot Sight Shader";
    Version = 3;
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
    #define BLEND_MODE_ALREADY_SET 1
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
        PixelInput o = ProcessVertex( i );
        return FinalizeVertex( o );
    }
}

PS
{
    StaticCombo( S_MODE_DEPTH, 0..1, Sys(ALL) );
    DynamicCombo( D_MULTIVIEW_INSTANCING, 0..1, Sys(PC) );

    RenderState( BlendEnable, true );
    RenderState( SrcBlend, SRC_ALPHA );
    RenderState( DstBlend, INV_SRC_ALPHA );

    #define DEPTH_STATE_ALREADY_SET 1

    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    #include "common/classes/Depth.hlsl"

    BoolAttribute( bWantsFBCopyTexture, true );

    Texture2D g_tFrameBufferCopyTexture < Attribute( "FrameBufferCopyTexture" ); SrgbRead( false ); >;

    //
    // Glass settings
    //
    float g_flRefractionStrength < Default( 1.005 ); Range( 1.0, 1.1 ); UiGroup( "Glass,10/10" ); >;

    //
    // Sight dot settings
    //
    float3 g_vSightLightColor < UiType( Color ); Default3( 1.0, 0.0, 0.0 ); UiGroup( "Sight Dot,10/10" ); >;
    float g_flSightDistanceScale < Default( 3.0 ); Range( 0.0, 20.0 ); UiGroup( "Sight Dot,10/20" ); >;

    CreateInputTexture2D( RedDot, Linear, 8, "", "_color", "Sight Dot,10/30", Default3( 0.0, 0.0, 0.0 ) );
    Texture2D g_tRedDot < Channel( R, Box( RedDot ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );

        #if S_MODE_DEPTH
        {
            return float4( 1, 1, 1, 1 );
        }
        #endif

        m.Metalness = 0;

        float3 vViewRayWs = normalize( i.vPositionWithOffsetWs.xyz );
        float flNDotV = saturate( dot( -m.Normal, vViewRayWs ) );
        float3 vEnvBRDF = CalcBRDFReflectionFactor( flNDotV, m.Roughness, 0.04 );

        //
        // Refraction - sample what is behind the glass
        //
        float flDepthPs = 1.0f - Depth::GetNormalized( i.vPositionSs.xy );
        float3 vRefractionWs = RecoverWorldPosFromProjectedDepthAndRay( flDepthPs, vViewRayWs ) - g_vCameraPositionWs;
        float flDistanceVs = distance( i.vPositionWithOffsetWs.xyz, vRefractionWs );

        float3 vRefractRayWs = refract( vViewRayWs, m.Normal, 1.0 / g_flRefractionStrength );
        float3 vRefractWorldPosWs = i.vPositionWithOffsetWs.xyz + vRefractRayWs * flDistanceVs;

        float4 vPositionPs = Position4WsToPs( float4( vRefractWorldPosWs, 0 ) );
        float2 vPositionSs = vPositionPs.xy / vPositionPs.w;
        vPositionSs = vPositionSs * 0.5 + 0.5;
        vPositionSs.y = 1.0 - vPositionSs.y;

        #if ( D_MULTIVIEW_INSTANCING )
        {
            vPositionSs.x *= 0.5;
        }
        #endif

        float2 vUV = vPositionSs * g_vFrameBufferCopyInvSizeAndUvScale.zw;
        float4 vRefractionColor = g_tFrameBufferCopyTexture.SampleLevel( g_sTrilinearMirror, vUV, 0 );

        // Glass tint / emission from refracted scene
        m.Emission = lerp( vRefractionColor.xyz, 0.0f, vEnvBRDF ) * m.Albedo;
        m.Albedo = 0;

        //
        // Sight dot - projected collimator style
        //
        float3 vCameraDir = normalize( i.vPositionWithOffsetWs );
        float flProjectDirOntoNormal = 1.0f / dot( vCameraDir, m.Normal );
        float flProjectA = -g_flSightDistanceScale * flProjectDirOntoNormal;

        float flProjectU = dot( vCameraDir, i.vTangentUWs );
        float flProjectV = dot( vCameraDir, i.vTangentVWs );

        float2 vRedDotUV = saturate( i.vTextureCoords.xy + ( flProjectA * 0.5 ) * float2( flProjectU, flProjectV ) );
        float flRedDot = g_tRedDot.SampleLevel( g_sAniso, vRedDotUV, 0 ).r;

        float3 vDotEmission = g_vSightLightColor * 20.0f;
        m.Emission = lerp( m.Emission, vDotEmission, saturate( flRedDot ) );

        // Glass transparency — grazing angles are more opaque
        float flAlpha = saturate( flNDotV * 0.7f + 0.3f + flRedDot );

        float4 result = ShadingModelStandard::Shade( i, m );
        result.a = flAlpha;
        return result;
    }
}