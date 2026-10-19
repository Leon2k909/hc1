"""Stage continuous structural timber; keep the generated albedo byte-exact."""
import hashlib
import json
from pathlib import Path
import shutil
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'Sources/Lowtide/structure'
STAGE = HERE / 'stage'
GENERATED = Path('C:/Users/leon2/.codex/generated_images/01a13277-1c4d-7843-b382-ae43679cb8fa/exec-cdd3a2ee-b607-4719-9437-c562fbadd6d2.png')
SHADER = 'shaders/hc1_lowtide_structure_v2.shader'
RESOURCE = 'materials/lowtide/structure'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')

SOURCE.mkdir(parents=True, exist_ok=True)
source = SOURCE / 'beam-timber-source.png'
if source.exists():
    assert digest(source) == digest(GENERATED), 'Existing timber source differs'
else:
    shutil.copyfile(GENERATED, source)

rgb = np.asarray(Image.open(source).convert('RGB'), np.float32) / 255
lum = rgb @ np.array([.2126, .7152, .0722], np.float32)
# Shallow fibre relief, not image brightness used as macro displacement.
height = (gaussian_filter(lum, 1.0, mode='wrap') - gaussian_filter(lum, 22, mode='wrap')) * .0012
dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * rgb.shape[1] / (2 * .6)
dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * rgb.shape[0] / (2 * 2.4)
normal = np.stack([-dx, dy, np.ones_like(dx)], axis=2)
normal /= np.linalg.norm(normal, axis=2, keepdims=True)
rough = np.clip(.77 + (gaussian_filter(lum, 3, mode='wrap') - lum) * .6, .66, .9)
target = STAGE / RESOURCE
target.mkdir(parents=True, exist_ok=True)
shutil.copyfile(source, target / 'beam_timber_color.png')
Image.fromarray(np.rint((normal * .5 + .5) * 255).clip(0, 255).astype(np.uint8)).save(target / 'beam_timber_normal.png')
Image.fromarray(np.rint(rough * 255).astype(np.uint8)).save(target / 'beam_timber_rough.png')

shader = '''HEADER
{
    Description = "Lowtide solid timber and aged cast iron";
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
    // Opaque RGB mips preserve the unmodified non-power-of-two generated scan.
    #define AlphaWeighted( color, opacity ) Box( color )
    #include "common/utils/Material.CommonInputs.hlsl"
    #undef AlphaWeighted
    #include "common/pixel.hlsl"
    float3 g_vStructureTint < Default3( 1, 1, 1 ); UiType( Color ); >;
    float2 g_vStructureUvScale < Default2( 1, 1 ); >;
    float g_flStructureRoughnessScale < Default( 1 ); Range( 0, 2 ); >;
    float g_flStructureRoughnessFloor < Default( .55 ); Range( 0, 1 ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        i.vTextureCoords.xy *= g_vStructureUvScale;
        Material m = Material::From( i );
        m.Albedo *= g_vStructureTint;
        m.Roughness = saturate( max( m.Roughness * g_flStructureRoughnessScale, g_flStructureRoughnessFloor ) );
        m.Metalness = 0;
        m.Transmission = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
'''
write(STAGE / SHADER, shader)
write(SOURCE / 'structure-v2.shader', shader)

def material(prefix, tint, uv, floor, scale=1):
    return f'''"Layer0"
{{
    shader "{SHADER}"
    TextureColor "{prefix}_color.png"
    TextureNormal "{prefix}_normal.png"
    TextureRoughness "{prefix}_rough.png"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vStructureTint "[{tint}]"
    g_vStructureUvScale "[{uv}]"
    g_flStructureRoughnessScale "{scale}"
    g_flStructureRoughnessFloor "{floor}"
}}
'''
write(target / 'lt_beam_timber_v2.vmat', material(f'{RESOURCE}/beam_timber', '.72 .70 .66', '1.354666667 .338666667', .7))
write(target / 'lt_cast_iron_v2.vmat', material('materials/lowtide/drainage/cast_iron', '.85 .85 .85', '2.666666667 2.666666667', .55, .9))

resources = sorted(p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file() and p.suffix != '.meta')
for relative in resources:
    write(Path(str(STAGE / relative) + '.meta'), json.dumps({'guid': str(uuid.uuid5(uuid.NAMESPACE_URL, relative))}, indent=2) + '\n')
protected_paths = [f'Assets/models/maps/lowtide/lowtide_{bank}.{ext}' for bank in ('east', 'west', 'dress_east', 'dress_west') for ext in ('obj', 'vmdl')]
protected_paths += ['Assets/scenes/maps/Lowtide/lowtide.scene', 'Sources/Lowtide/lighting/warehouse-lighting.json']
protected_paths += [f'Assets/materials/lowtide/drainage/cast_iron_{x}.png' for x in ('color', 'normal', 'rough')]
report = {
    'source': source.relative_to(ROOT).as_posix(), 'sourceSha256': digest(source),
    'generatedAlbedoUnchanged': digest(source) == digest(target / 'beam_timber_color.png'),
    'size': list(rgb.shape[:2][::-1]), 'physicalMetres': [.6, 2.4], 'grainAxis': 'V follows each polygon longest edge',
    'normalDepthMetres': .0012, 'normalMaximumSlope': float(np.max(np.hypot(dx, dy))),
    'roughnessRange': [float(rough.min()), float(rough.max())],
    'assets': {p.relative_to(STAGE).as_posix(): digest(p) for p in sorted(STAGE.rglob('*')) if p.is_file()},
    'protected': {p: digest(ROOT / p) for p in protected_paths},
    'nativeReviewed': False, 'productionBound': False,
}
write(HERE / 'manifest.json', json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('assets', 'protected')}, indent=2))
