#ifndef MATERIAL_COMMON_INPUTS_HLSL
#define MATERIAL_COMMON_INPUTS_HLSL

#include "common/utils/normal.hlsl"

// The generated RGBA atlas owns its alpha. Keep it in the compiled colour
// texture instead of treating the atlas's RGB as an opacity mask.
CreateInputTexture2D( TextureColor, Srgb, 8, "", "_color", "Material,10/10", Default4( 1, 1, 1, 1 ) );
CreateInputTexture2D( TextureNormal, Linear, 8, "NormalizeNormals", "_normal", "Material,10/20", Default3( .5, .5, 1 ) );
CreateInputTexture2D( TextureRoughness, Linear, 8, "", "_rough", "Material,10/30", Default( .75 ) );
CreateInputTexture2D( TextureMetalness, Linear, 8, "", "_metal", "Material,10/40", Default( 0 ) );
CreateInputTexture2D( TextureAmbientOcclusion, Linear, 8, "", "_ao", "Material,10/50", Default( 1 ) );
CreateInputTexture2D( TextureBlendMask, Linear, 8, "", "_blend", "Material,10/60", Default( 0 ) );
CreateInputTexture2D( TextureTintMask, Linear, 8, "", "_tint", "Material,10/70", Default( 1 ) );

float3 g_flTintColor < Default3( 1, 1, 1 ); UiGroup( "Material,10/90" ); UiType( Color ); >;
float g_flSelfIllumScale < Default( 0 ); UiGroup( "Material,10/91" ); >;

Texture2D g_tColor < Channel( RGBA, Box( TextureColor ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
Texture2D g_tNormal < Channel( RGB, Box( TextureNormal ), Linear ); Channel( A, Box( TextureTintMask ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
Texture2D g_tRma < Channel( R, Box( TextureRoughness ), Linear ); Channel( G, Box( TextureMetalness ), Linear ); Channel( B, Box( TextureAmbientOcclusion ), Linear ); Channel( A, Box( TextureBlendMask ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;

#define MATERIAL_ALPHA_TEXTURE g_tColor
TextureAttribute( LightSim_DiffuseAlbedoTexture, g_tColor );
TextureAttribute( RepresentativeTexture, g_tColor );
BoolAttribute( DoNotCastShadows, F_DO_NOT_CAST_SHADOWS ? true : false );
BoolAttribute( SupportsMappingDimensions, true );
BoolAttribute( renderbackfaces, F_RENDER_BACKFACES ? true : false );
SamplerState TextureFiltering < Filter( ANISOTROPIC ); MaxAniso( 8 ); AddressU( WRAP ); AddressV( WRAP ); >;

#endif
