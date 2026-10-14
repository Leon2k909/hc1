HEADER
{
    Description = "Belltower sealed windows: reflective glass and parallax interiors";
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
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    CreateInputTexture2D( TextureRoomBack, Srgb, 8, "", "_color", "Interior", Default3( .1, .1, .1 ) );
    CreateInputTexture2D( TextureRoomWall, Srgb, 8, "", "_color", "Interior", Default3( .2, .2, .2 ) );
    Texture2D g_tRoomBack < Channel( RGB, Box( TextureRoomBack ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tRoomWall < Channel( RGB, Box( TextureRoomWall ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState RoomSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flInteriorBrightness < Default( .13 ); Range( 0, 2 ); >;
    float g_flRoomDepth < Default( 34 ); Range( 8, 120 ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        m.Albedo = float3( .003, .005, .006 );
        m.Metalness = 0;
        m.Roughness = .16;
        m.Transmission = 0;
        m.Normal = normalize( i.vNormalWs );
        #if !S_MODE_DEPTH
        {
            float2 uv = float2( i.vTextureCoords.x, 1-i.vTextureCoords.y );
            float3 n = normalize( i.vNormalWs );
            float3 right = normalize( cross( float3( 0, 0, 1 ), n ) );
            float3 view = normalize( g_vCameraPositionWs - m.WorldPosition );
            float2 dx = ddx( uv ), dy = ddy( uv );
            float determinant = dx.x * dy.y - dx.y * dy.x;
            determinant = abs( determinant ) < 1e-10 ? 1e-10 : determinant;
            float3 du = ( ddx( m.WorldPosition ) * dy.y - ddy( m.WorldPosition ) * dx.y ) / determinant;
            float3 dv = ( ddy( m.WorldPosition ) * dx.x - ddx( m.WorldPosition ) * dy.x ) / determinant;
            float width = clamp( length( du ), 20, 120 );
            float height = clamp( length( dv ), 40, 180 );
            float3 origin = float3( saturate( uv ), 0 );
            float3 ray = float3( -dot( view, right ), -view.z, max( dot( view, n ), .001 ) ) / float3( width, height, g_flRoomDepth );
            float3 safeRay = ( step( 0, ray ) * 2 - 1 ) * max( abs( ray ), .000001 );
            float3 distances = ( step( 0, ray ) - origin ) / safeRay;
            float travel = min( distances.x, min( distances.y, distances.z ) );
            float3 hit = saturate( origin + ray * travel );
            float3 room;
            if ( distances.z <= min( distances.x, distances.y ) )
                room = g_tRoomBack.Sample( RoomSampler, float2( hit.x, 1-hit.y ) * .92 + .04 ).rgb;
            else if ( distances.x < distances.y )
            {
                room = g_tRoomWall.Sample( RoomSampler, frac( hit.zy * float2( 1.3, 2.0 ) ) ).rgb;
                room *= float3( .38, .34, .29 ) * lerp( 1, .45, hit.z );
            }
            else
            {
                room = g_tRoomWall.Sample( RoomSampler, frac( hit.xz * 1.6 ) ).rgb;
                room *= hit.y < .5 ? float3( .26, .18, .12 ) : float3( .20, .20, .18 );
            }
            float fresnel = .04 + .96 * pow( 1-saturate( dot( n, view ) ), 5 );
            m.Emission = room * g_flInteriorBrightness * (1-fresnel);
        }
        #endif
        return ShadingModelStandard::Shade( i, m );
    }
}
