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
