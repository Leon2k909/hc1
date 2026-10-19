HEADER
{
    Description = "Lowtide troweled warehouse concrete";
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
    CreateInputTexture2D( TextureFloorContact, Linear, 8, "", "_ao", "Floor contact", Default3( 1, 1, 1 ) );
    Texture2D g_tFloorContact < Channel( RGB, Box( TextureFloorContact ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState FloorContactSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flFloorContact < Default( 0 ); Range( 0, 1 ); >;
    float g_flConcreteScale < Default( 3.2512 ); Range( .25, 16 ); >;

    float ConcreteNoise( float2 p )
    {
        float2 cell = floor( p ), f = frac( p );
        f = f * f * ( 3 - 2 * f );
        float4 h = float4( dot( cell, float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 0 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 0, 1 ), float2( 127.1, 311.7 ) ),
            dot( cell + 1, float2( 127.1, 311.7 ) ) );
        h = frac( sin( h ) * 43758.5453 );
        return lerp( lerp( h.x, h.y, f.x ), lerp( h.z, h.w, f.x ), f.y );
    }

    CreateInputTexture2D( TextureWarehouseUse, Linear, 8, "", "_use", "Warehouse use", Default3( 0, 0, 0 ) );
    Texture2D g_tWarehouseUse < Channel( RGB, Box( TextureWarehouseUse ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState WarehouseUseSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flWarehouseUse < Default( 0 ); Range( 0, 1 ); >;

    void ApplyWarehouseUse( PixelInput input, inout Material material )
    {
        float east = -material.WorldPosition.y;
        float north = material.WorldPosition.x;
        // Match the existing concrete-contact scope exactly: no outdoor slabs,
        // upright surfaces or mezzanines receive these warehouse traffic marks.
        if ( g_flWarehouseUse <= 0 || abs( material.WorldPosition.z ) >= .1 || input.vNormalWs.z <= .98
            || abs( east ) <= 240 || abs( east ) >= 1000 || north <= -400 || north >= 1150 )
            return;
        float2 uv = float2( ( abs( east ) - 240 ) / 760, 1 - ( north + 400 ) / 1550 );
        uv = clamp( uv, float2( .5 / 1024, .5 / 2048 ), 1 - float2( .5 / 1024, .5 / 2048 ) );
        uv.x = uv.x * .5 + ( east < 0 ? .5 : 0 );
        float3 use = g_tWarehouseUse.Sample( WarehouseUseSampler, uv ).rgb * g_flWarehouseUse;
        material.Albedo = lerp( material.Albedo, float3( .145, .132, .112 ), use.r * .30 );
        material.Albedo *= 1 - use.g * .50;
        // Preserve the existing surface exactly at zero mask, even if its
        // original roughness already lies outside the new wear limits.
        material.Roughness = clamp( material.Roughness + use.r * .12 + use.g * .06 - use.b * .14,
            min( material.Roughness, .44 ), max( material.Roughness, .95 ) );
        // Repeated traffic smooths the existing microscopic concrete grain.
        material.Normal = normalize( lerp( material.Normal, normalize( input.vNormalWs ), use.b * .22 ) );
    }

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        i.vTextureCoords.xy *= g_flConcreteScale;
        Material m = Material::From( i );
        float2 ground = m.WorldPosition.xy;
        float patina = ConcreteNoise( ground / 170 ) * .65 + ConcreteNoise( ground / 47 + 11.4 ) * .35;
        m.Albedo *= lerp( .82, 1.03, patina );
        // Broad polished patches vary the response without baked illumination.
        m.Roughness = saturate( m.Roughness + ( patina - .5 ) * .18 );
        // Static diffuse occlusion for the two concrete warehouse floors only.
        // The bake is made from saved architecture/cargo, not a painted shadow.
        // Other concrete, vertical faces and elevated surfaces remain unmasked.
        float east = -m.WorldPosition.y;
        float north = m.WorldPosition.x;
        if ( g_flFloorContact > 0 && abs( m.WorldPosition.z ) < .1 && i.vNormalWs.z > .98
            && abs( east ) > 240 && abs( east ) < 1000 && north > -400 && north < 1150 )
        {
            float2 uv = float2( ( abs( east ) - 240 ) / 760, 1 - ( north + 400 ) / 1550 );
            // Each atlas cell is 384 x 768. Clamp to its own texel centres.
            uv = clamp( uv, float2( .5 / 384, .5 / 768 ), 1 - float2( .5 / 384, .5 / 768 ) );
            uv.x = uv.x * .5 + ( east < 0 ? .5 : 0 );
            float2 contact = g_tFloorContact.Sample( FloorContactSampler, uv ).rg;
            float visibility = lerp( 1, contact.r, .85 ) * lerp( 1, contact.g, .45 );
            m.AmbientOcclusion *= lerp( 1, visibility, g_flFloorContact );
        }
        ApplyWarehouseUse( i, m );
        m.Metalness = 0;
        m.Transmission = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
