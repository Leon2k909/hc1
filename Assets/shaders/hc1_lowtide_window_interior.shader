HEADER
{
    Description = "Lowtide sealed-window glass with view-dependent warehouse interiors";
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
    CreateInputTexture2D( TextureRoomWood, Srgb, 8, "", "_color", "Interior", Default3( .1, .1, .1 ) );
    Texture2D g_tRoomBack < Channel( RGB, Box( TextureRoomBack ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tRoomWall < Channel( RGB, Box( TextureRoomWall ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    Texture2D g_tRoomWood < Channel( RGB, Box( TextureRoomWood ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState RoomSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flInteriorBrightness < Default( .16 ); Range( 0, 2 ); >;
    float g_flRoomDepth < Default( 32 ); Range( 8, 240 ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        float2 authoredUv = i.vTextureCoords.xy;
        float variant = floor( authoredUv.x * .5 );
        // OBJ import flips V; reconstruct the authored, upward room coordinate.
        float2 uv = float2( authoredUv.x - variant * 2, 1 - authoredUv.y );
        i.vTextureCoords.xy = uv;
        Material m = Material::From( i );
        m.Metalness = 0;
        m.Transmission = 0;
        m.Albedo = float3( .003, .005, .005 );
        m.Roughness = clamp( m.Roughness * .5, .09, .24 );
        #if !S_MODE_DEPTH
        {
            // Interior mapping follows van Dongen (CGI 2008): ray/plane hits
            // supply parallax without extra room meshes or gameplay openings.
            // https://www.proun-game.com/Oogst3D/CODING/InteriorMapping/InteriorMapping.pdf
            float3 n = normalize( i.vNormalWs );
            float3 right = normalize( cross( float3( 0, 0, 1 ), n ) );
            float3 view = normalize( g_vCameraPositionWs - m.WorldPosition );
            float2 dx = ddx( uv ), dy = ddy( uv );
            float determinant = dx.x * dy.y - dx.y * dy.x;
            determinant = abs( determinant ) < 1e-10 ? 1e-10 : determinant;
            float3 du = ( ddx( m.WorldPosition ) * dy.y - ddy( m.WorldPosition ) * dx.y ) / determinant;
            float3 dv = ( ddy( m.WorldPosition ) * dx.x - ddx( m.WorldPosition ) * dy.x ) / determinant;
            float width = clamp( length( du ), 12, 100 );
            float height = clamp( length( dv ), 40, 180 );
            // The back-wall atlas cells are square. Keep their physical aspect
            // ratio even on the tall, narrow warehouse windows.
            float roomSpan = max( width * 1.5, height * 1.1 );
            float3 size = float3( roomSpan, roomSpan, g_flRoomDepth * width / 40 );
            float3 origin = float3( .5 + ( uv.x - .5 ) * width / size.x,
                                   .5 + ( uv.y - .5 ) * height / size.y, 0 );
            // V is upwards in the authored OBJ; texture sampling below flips it.
            float3 ray = float3( -dot( view, right ), -view.z, max( dot( view, n ), .001 ) ) / size;
            float3 safeRay = ( step( 0, ray ) * 2 - 1 ) * max( abs( ray ), .000001 );
            float3 distances = ( step( 0, ray ) - origin ) / safeRay;
            float travel = min( distances.x, min( distances.y, distances.z ) );
            float3 hit = saturate( origin + ray * travel );
            float3 room;
            if ( distances.z <= min( distances.x, distances.y ) )
            {
                float2 cell = float2( fmod( variant, 2 ), floor( variant * .5 ) );
                // Keep all atlas samples inside their cell, clear of its seams.
                float2 atlas = ( cell + .012 + float2( hit.x, 1-hit.y ) * .976 ) * .5;
                room = g_tRoomBack.Sample( RoomSampler, atlas ).rgb;
            }
            else if ( distances.x < distances.y )
            {
                float2 wallUv = frac( float2( hit.z * 1.7, hit.y * 1.4 ) ) * .610 + .001;
                room = g_tRoomWall.Sample( RoomSampler, wallUv ).rgb * float3( .20, .18, .15 );
                room *= lerp( 1.1, .45, hit.z );
            }
            else
            {
                room = g_tRoomWood.Sample( RoomSampler, frac( hit.xz * float2( 1.3, 1.7 ) ) ).rgb;
                room *= hit.y < .5 ? float3( .44, .39, .32 ) : float3( .19, .17, .14 );
            }
            float fresnel = .04 + .96 * pow( 1 - saturate( dot( n, view ) ), 5 );
            float occupancy = lerp( .40, 1.0, frac( sin( variant * 13.71 + 4.2 ) * 451.13 ) );
            m.Emission = room * g_flInteriorBrightness * occupancy * ( 1-fresnel );
        }
        #endif
        return ShadingModelStandard::Shade( i, m );
    }
}
