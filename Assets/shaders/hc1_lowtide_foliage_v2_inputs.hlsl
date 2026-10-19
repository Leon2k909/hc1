#ifndef MATERIAL_COMMON_INPUTS_HLSL
#define MATERIAL_COMMON_INPUTS_HLSL
#include "common/utils/normal.hlsl"
CreateInputTexture2D( TextureColor, Srgb, 8, "", "_color", "Material,10/10", Default4(1,1,1,1) );
CreateInputTexture2D( TextureCoverage, Linear, 8, "", "_coverage", "Material,10/20", Default4(1,1,1,1) );
CreateInputTexture2D( TextureNormal, Linear, 8, "", "_normal", "Material,10/30", Default4(.5,.5,1,1) );
CreateInputTexture2D( TextureSurface, Linear, 8, "", "_surface", "Material,10/40", Default4(.75,0,1,1) );
float3 g_flTintColor < Default3(1,1,1); UiGroup("Material,10/90"); UiType(Color); >;
float g_flSelfIllumScale < Default(0); UiGroup("Material,10/91"); >;
Texture2D g_tColor < Channel(RGBA, Box(TextureColor), Srgb); OutputFormat(BC7); SrgbRead(true); >;
Texture2D g_tCoverage < Channel(RGBA, Box(TextureCoverage), Linear); OutputFormat(BC7); SrgbRead(false); >;
Texture2D g_tNormal < Channel(RGBA, Box(TextureNormal), Linear); OutputFormat(BC7); SrgbRead(false); >;
Texture2D g_tRma < Channel(RGBA, Box(TextureSurface), Linear); OutputFormat(BC7); SrgbRead(false); >;
#define MATERIAL_ALPHA_TEXTURE g_tCoverage
TextureAttribute(LightSim_DiffuseAlbedoTexture, g_tColor);
TextureAttribute(RepresentativeTexture, g_tColor);
BoolAttribute(DoNotCastShadows, F_DO_NOT_CAST_SHADOWS ? true : false);
BoolAttribute(SupportsMappingDimensions, true);
BoolAttribute(renderbackfaces, F_RENDER_BACKFACES ? true : false);
#ifndef CUSTOM_TEXTURE_FILTERING
SamplerState TextureFiltering < Filter((F_TEXTURE_FILTERING == 0 ? ANISOTROPIC : (F_TEXTURE_FILTERING == 1 ? BILINEAR : (F_TEXTURE_FILTERING == 2 ? TRILINEAR : (F_TEXTURE_FILTERING == 3 ? POINT : NEAREST))))); MaxAniso(8); >;
#endif
#endif
