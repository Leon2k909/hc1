    CreateInputTexture2D( TexturePavingUse, Linear, 8, "", "_use", "Paving use", Default3( 0, 0, 0 ) );
    Texture2D g_tPavingUse < Channel( RGB, Box( TexturePavingUse ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState PavingUseSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float4 g_vPavingUseBounds < Default4( -2800, -1700, 5600, 3200 ); >;
    float g_flPavingUse < Default( 0 ); Range( 0, 1 ); >;

    float3 PavingUse( PixelInput input, float3 world )
    {
        float2 plan = float2( -world.y, world.x );
        float2 uv = ( plan - g_vPavingUseBounds.xy ) / g_vPavingUseBounds.zw;
        uv.y = 1 - uv.y;
        // Derivatives remain defined across every surface and atlas boundary.
        float2 dx = ddx( uv ), dy = ddy( uv );
        float scope = ( abs( world.z ) < .1 && input.vNormalWs.z > .98
            && all( uv >= 0 ) && all( uv <= 1 ) ) ? g_flPavingUse : 0;
        float3 use = g_tPavingUse.SampleGrad( PavingUseSampler, uv, dx, dy ).rgb;
        return use * scope;
    }
