HEADER
{
    Description = "Lowtide masonry: seamless scanned clay, recessed mortar and physical brick scale";
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
    PixelInput MainVs( VertexInput input ) { return FinalizeVertex( ProcessVertex( input ) ); }
}
PS
{
    #define CUSTOM_TEXTURE_FILTERING 1
    SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;
    #include "common/utils/Material.CommonInputs.hlsl"
    #include "common/pixel.hlsl"
    #include "common/lowtide_shed_wear.hlsl"
    float4 g_vBrickScale < Default4( 1, 1, 0, 0 ); UiGroup( "Brick" ); >;
    CreateInputTexture2D( TextureFacadeWear, Linear, 8, "", "_mask", "Facade", Default3( 0, 0, 0 ) );
    Texture2D g_tFacadeWear < Channel( RGB, Box( TextureFacadeWear ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState FacadeSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flFacadeWear < Default( 0 ); Range( 0, 2 ); >;
    CreateInputTexture2D( TextureCanalBiofilm, Srgb, 8, "", "_color", "Weathering", Default3( .2, .22, .15 ) );
    Texture2D g_tCanalBiofilm < Channel( RGB, Box( TextureCanalBiofilm ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    float g_flCanalBiofilm < Default( 0 ); Range( 0, 1 ); >;
    float g_flTidalClay < Default( 0 ); Range( 0, 1 ); >;

    float3 FacadeWear( float3 world, float3 normal )
    {
        // Tools/lowtide_facade.py bakes these eight architectural elevations.
        // Restrict the mask to the outward faces, excluding interior walls,
        // separate buildings, pitched roofs and the projecting loading oriels.
        float e = -world.y, n = world.x, a = abs( e );
        float column = -1, along = 0;
        if ( world.z < 0 || world.z > 1024 ) return 0;
        if ( abs( a - 240 ) < 6 && normal.y * sign( e ) > .8 )
        { column = 0; along = ( n + 400 ) / 1550; }
        else if ( abs( a - 1000 ) < 6 && normal.y * sign( e ) < -.8 )
        { column = 1; along = ( n + 400 ) / 1550; }
        else if ( abs( n - 1150 ) < 6 && normal.x > .8 )
        { column = 2; along = ( a - 240 ) / 760; }
        else if ( abs( n + 400 ) < 6 && normal.x < -.8 )
        { column = 3; along = ( a - 240 ) / 760; }
        if ( column < 0 || along < 0 || along > 1 ) return 0;
        float2 local = float2( along, 1 - world.z / 1024 );
        // Eight-pixel gutters and pixel-centre coordinates prevent cell bleed.
        float2 atlas = ( float2( column, e < 0 ? 1 : 0 ) + ( 8.5 + local * 1007 ) / 1024 ) / float2( 4, 2 );
        return g_tFacadeWear.Sample( FacadeSampler, atlas ).rgb;
    }

    float BrickNoise( float2 p )
    {
        float2 cell = floor( p );
        float2 blend = frac( p );
        blend = blend * blend * ( 3.0 - 2.0 * blend );
        float4 dots = float4( dot( cell, float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 0 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 0, 1 ), float2( 127.1, 311.7 ) ),
            dot( cell + float2( 1, 1 ), float2( 127.1, 311.7 ) ) );
        float4 values = frac( sin( dots ) * 43758.5453 );
        return lerp( lerp( values.x, values.y, blend.x ), lerp( values.z, values.w, blend.x ), blend.y );
    }

    float4 MainPs( PixelInput input ) : SV_Target0
    {
        float2 worldUv = input.vTextureCoords.xy;
        // Preserve UV derivatives across repeats: the wrapping sampler handles the tile boundary and mipmaps.
        input.vTextureCoords.xy *= g_vBrickScale.xy;
        Material material = Material::From( input );
        // CommonInputs defaults metalness and transmission to one. Fired clay and mortar are opaque dielectrics.
        material.Metalness = 0.0;
        material.Transmission = 0.0;
        float3 world = material.WorldPosition;
        // Older canal cards used separate dark tints with a ruler-straight
        // boundary. Match the clay above; world-space moisture supplies the
        // gradual colour change across those retained geometry sections.
        if ( g_flTidalClay > 0 && world.z < -45 && abs( world.y ) > 235 && abs( world.y ) < 245 )
        {
            float3 sideTint = world.y > 0 ? float3( .66, .58, .54 ) : float3( 1, 1, 1 );
            material.Albedo *= sideTint / max( g_flTintColor, .01 );
            material.Roughness = .60;
        }
        float along = abs( input.vNormalWs.x ) > .65 ? world.y : world.x;
        float2 wall = float2( along, world.z );
        // Metre-scale staining is anchored to the building, independent of tile UVs.
        float macro = BrickNoise( wall / float2( 230, 175 ) );
        float rain = BrickNoise( wall / float2( 22, 155 ) + 17.3 );
        float fine = BrickNoise( wall / float2( 5, 42 ) + 43.1 );
        float vertical = 1 - smoothstep( .25, .7, abs( input.vNormalWs.z ) );
        float grime = smoothstep( .40, .78, rain * .72 + fine * .28 ) * vertical;
        material.Albedo *= lerp( .72, 1.07, macro ) * ( 1 - grime * .19 );
        // Salt deposition is sparse and broken, never an even white stripe.
        float salt = smoothstep( .65, .82, BrickNoise( wall / float2( 48, 65 ) + 80 ) );
        salt *= smoothstep( .4, .7, fine ) * vertical * .045;
        material.Albedo = lerp( material.Albedo, float3( .38, .35, .29 ), salt );
        // The canal retains moisture below the quay; irregular tide height hides
        // the old hard material boundary without moving any collision geometry.
        float tide = -30 + 21 * BrickNoise( float2( along / 58, 7.2 ) );
        float damp = ( 1 - smoothstep( tide - 75, tide + 8, world.z ) ) * vertical;
        material.Albedo *= lerp( float3( 1, 1, 1 ), float3( .49, .62, .45 ), damp );
        material.Roughness = lerp( material.Roughness, .39, damp * .8 );
        #if !S_MODE_DEPTH
        if ( g_flCanalBiofilm > 0 && world.z < 100 )
        {
            float e = -world.y, n = world.x, a = abs( e );
            float3 face = normalize( input.vNormalWs );
            // Exterior normals and tight position bands exclude the playable
            // warehouse interior. The low canal wall includes its coping top.
            float canal = ( a > 215 && a < 270 && n > -1450 && n < 1450 &&
                ( face.y * sign( e ) > .6 || face.z > .6 ) ) ? 1 : 0;
            float outside = ( a > 985 && a < 1015 && n > -410 && n < 1160 && face.y * sign( e ) < -.6 ) ? 1 : 0;
            float ends = ( a > 230 && a < 1010 &&
                ( ( abs( n + 400 ) < 14 && face.x < -.6 ) || ( abs( n - 1150 ) < 14 && face.x > .6 ) ) ) ? 1 : 0;
            float exterior = max( canal, max( outside, ends ) );
            float ground = 1 - smoothstep( 15 + macro * 24, 55 + macro * 35, world.z );
            float patches = smoothstep( .29, .67, macro * .58 + fine * .42 );
            float coverage = ground * ( .22 + patches * .68 ) * exterior * g_flCanalBiofilm;
            float2 bioUv = abs( face.z ) > .6 ? world.xy : wall;
            float3 bio = g_tCanalBiofilm.Sample( TextureFiltering, bioUv / 59.055 ).rgb;
            // Retain the original masonry joints and normal map through thin
            // crust, with wetter roughness only below the tide's drying zone.
            material.Albedo = lerp( material.Albedo, bio * .72, coverage );
            float wetness = 1 - smoothstep( -105, -25, world.z );
            material.Roughness = lerp( material.Roughness, lerp( .87, .42, wetness ), coverage );
        }
        if ( g_flFacadeWear > 0 )
        {
            float3 wear = FacadeWear( world, normalize( input.vNormalWs ) ) * g_flFacadeWear;
            // Deposits follow actual sills and projecting courses. Contact
            // occlusion affects ambient lighting; soot changes the clay itself.
            material.AmbientOcclusion *= 1 - saturate( wear.r * .55 );
            material.Albedo *= 1 - saturate( wear.g * .48 + wear.r * .14 );
            material.Albedo = lerp( material.Albedo, float3( .31, .29, .25 ), saturate( wear.b * .5 ) );
            material.Roughness = saturate( material.Roughness + wear.g * .08 );
        }
        if ( g_flShedWear > 0 )
        {
            float3 deposits = ShedWear( world, normalize( input.vNormalWs ) ) * g_flShedWear;
            material.AmbientOcclusion *= 1 - saturate( deposits.r * .65 );
            material.Albedo *= 1 - saturate( deposits.g * .62 + deposits.r * .10 );
            material.Albedo = lerp( material.Albedo, float3( .31, .29, .25 ), deposits.b * .35 );
            material.Roughness = saturate( material.Roughness + deposits.g * .07 );
        }
        #endif
        return ShadingModelStandard::Shade( input, material );
    }
}
