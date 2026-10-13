HEADER
{
    Description = "Lowtide bridge steel: scanned paint, fine corrosion and physical edge wear";
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
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    float4 g_vSteelRegion < Default4( 0, 0, 1, 1 ); UiGroup( "Steel" ); >;
    float g_flSteelTile < Default( 24 ); Range( 4, 96 ); UiGroup( "Steel" ); >;
    float g_flEdgeWearWidth < Default( .11 ); Range( .01, .4 ); UiGroup( "Steel" ); >;

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        Material material = Material::Init( input );
        float2 face = input.vTextureCoords.xy;
        float2 uvDx = ddx( face ), uvDy = ddy( face );
        float3 worldDx = ddx( material.WorldPosition ), worldDy = ddy( material.WorldPosition );
        float determinant = uvDx.x * uvDy.y - uvDx.y * uvDy.x;
        float inverse = abs( determinant ) > 1e-10 ? 1 / determinant : 0;
        // Every rectangular steel face has its own 0..1 UVs. Recover its actual dimensions in inches,
        // so wear stays a few millimetres wide on a handrail, an upright or a diagonal brace.
        float3 alongU = ( worldDx * uvDy.y - worldDy * uvDx.y ) * inverse;
        float3 alongV = ( worldDy * uvDx.x - worldDx * uvDy.x ) * inverse;
        float2 dimensions = float2( length( alongU ), length( alongV ) );
        float3 axisU = alongU / max( dimensions.x, 1e-6 );
        float3 axisV = alongV / max( dimensions.y, 1e-6 );
        float2 surface = float2( dot( material.WorldPosition, axisU ), dot( material.WorldPosition, axisV ) ) / g_flSteelTile;
        float2 uv = g_vSteelRegion.xy + frac( surface ) * g_vSteelRegion.zw;
        float2 dx = ddx( surface ) * g_vSteelRegion.zw;
        float2 dy = ddy( surface ) * g_vSteelRegion.zw;
        // Explicit gradients keep filtering stable when the scan repeats or a long rail recedes from the camera.
        float4 albedo = g_tColor.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 normal = g_tNormal.SampleGrad( TextureFiltering, uv, dx, dy );
        float4 rma = g_tRma.SampleGrad( TextureFiltering, uv, dx, dy );
        material.Albedo = albedo.rgb * g_flTintColor * input.vVertexColor.rgb;
        material.Opacity = albedo.a;
        material.Normal = TransformNormal( DecodeNormal( normal.rgb ), input.vNormalWs, input.vTangentUWs, input.vTangentVWs );
        material.Roughness = rma.r;
        material.Metalness = rma.g;
        material.AmbientOcclusion = rma.b;

        float2 toEdge = saturate( min( face, 1 - face ) ) * dimensions;
        float edgeDistance = min( toEdge.x, toEdge.y );
        float wear = 1 - smoothstep( .015, g_flEdgeWearWidth, edgeDistance );
        float flecks = saturate( dot( albedo.rgb, float3( .2126, .7152, .0722 ) ) * 12 );
        wear *= .35 + .65 * flecks;
        material.Albedo = lerp( material.Albedo, float3( .15, .17, .18 ), wear * .65 );
        material.Metalness = lerp( material.Metalness, .75, wear );
        material.Roughness = lerp( material.Roughness, .38, wear );
        return ShadingModelStandard::Shade( material );
    }
}
