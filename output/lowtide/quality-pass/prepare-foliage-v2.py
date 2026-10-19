"""Stage the second foliage material outside Assets; native readbacks are required."""
from pathlib import Path
import hashlib
import json
import uuid

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Sources/Lowtide/foliage'
OUTPUT = ROOT / 'output/lowtide/quality-pass/foliage'
STAGE = OUTPUT / 'v2-stage'
PREFIX = 'materials/lowtide/foliage-v2/'
SHADER = 'shaders/hc1_lowtide_foliage_v2.shader'
INPUTS = 'shaders/hc1_lowtide_foliage_v2_inputs.hlsl'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    inputs = SOURCE / 'native-inputs'
    readback = json.loads((inputs / 'provenance.json').read_text())
    for item in readback['textures'].values():
        assert sha((inputs / item['file']).read_bytes()) == item['sha256'], item['file']
    manifest = OUTPUT / 'v2-manifest.json'
    assert not manifest.exists(), 'Inspect the prior manifest before retrying'
    changes = {}

    def put(relative, data, metadata=True):
        target = STAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        changes[relative] = sha(data)
        if metadata:
            meta = {'guid': str(uuid.uuid5(uuid.NAMESPACE_URL, 'hc1/lowtide/foliage-v2/' + relative))}
            put(relative + '.meta', (json.dumps(meta, indent=2) + '\n').encode(), False)

    shader = (SOURCE / 'hc1_lowtide_foliage.shader').read_text(encoding='cp1252')
    assert shader.count('Material m = Material::From( i );') == 1
    shader = shader.replace('hc1_lowtide_foliage_inputs.hlsl', 'hc1_lowtide_foliage_v2_inputs.hlsl')
    shader = shader.replace('native foliage lighting with direct RGBA colour input', 'native foliage lighting and original cutout coverage')
    shader = shader.replace('TextureAttribute( LightSim_Opacity_A, g_tColor );', 'TextureAttribute( LightSim_Opacity_A, g_tCoverage );')
    shader = shader.replace('Material m = Material::From( i );', '''Material m = Material::From( i );
        // Retain the generated atlas alpha, restricted to the original UV cutout.
        // Read the actual alpha channel; the template RGB never drives opacity.
        m.Opacity *= g_tCoverage.Sample( TextureFiltering, i.vTextureCoords.xy ).a;''')
    put(SHADER, shader.encode('utf-8'))
    put(INPUTS, b'''#ifndef MATERIAL_COMMON_INPUTS_HLSL
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
''', False)
    put(PREFIX + 'color.png', (SOURCE / 'oak-branch-candidate-v2.png').read_bytes())
    for item in readback['textures'].values():
        put(PREFIX + item['file'], (inputs / item['file']).read_bytes())
    parameters = {
        'shader': SHADER,
        'F_ALPHA_TEST': 1, 'F_RENDER_BACKFACES': 1, 'F_FOLIAGE_ANIMATION': 1,
        'F_TRANSMISSIVE': 1, 'F_GRAZING_FADE': 1,
        'TextureColor': PREFIX + 'color.png', 'TextureCoverage': PREFIX + 'coverage.png',
        'TextureNormal': PREFIX + 'normal.png', 'TextureSurface': PREFIX + 'surface.png',
        'TextureTransmissiveColor': PREFIX + 'transmission.png',
        'g_flTintColor': '[1 1 1]', 'g_flSelfIllumScale': 0,
        'g_flAlphaTestReference': .35, 'g_flAlphaDistanceStart': 800, 'g_flAlphaDistanceEnd': 2800,
        'g_flWrapAmount': .408, 'g_flWrapStrength': .45, 'g_flTransmissionScale': 8,
        'g_flAmbientBoost': 0, 'g_flMinRoughness': .75, 'g_flNormalVariation': .1,
        'g_flGrassNormalUp': .15, 'g_flGrazingFadeStart': .14, 'g_flGrazingFadeEnd': .118,
        'g_flAntiAliasedEdgeStrength': 1, 'g_flEdgeFrequency': .1, 'g_flEdgeAmplitude': 0,
        'g_flBranchFrequency': 3.171, 'g_flBranchAmplitude': 1,
        'g_flSwayStrength': 25, 'g_flSwaySpeed': 1, 'g_flDetailFadeDistance': 500,
        'g_flRimStrength': .193, 'g_flRimPower': 6.053,
    }
    material = '// Unassigned foliage comparison; original lighting response and UV coverage.\n"Layer0"\n{\n'
    material += ''.join(f'    {key} "{value}"\n' for key, value in parameters.items()) + '}\n'
    put(PREFIX + 'lt_oak_branch_v2.vmat', material.encode())
    protected = {}
    for directory in ('Assets/materials/lowtide', 'Assets/models/maps/lowtide', 'Assets/scenes/maps/Lowtide'):
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and not path.name.endswith('_c'):
                protected[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    for relative in ('models/sbox_props/trees/oak/tree_oak_medium_a.vmdl_c',
                     'models/sbox_props/trees/oak/oak_branch.vmat_c', 'models/sbox_props/trees/oak/oak_bark.vmat_c'):
        path = ROOT / '.sbox/cloud' / relative
        protected[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    manifest.write_text(json.dumps({'changes': changes, 'protected': protected,
        'status': 'Unassigned candidate; native compile and visual review required.'}, indent=2) + '\n')
    print(json.dumps({'candidate_files': len(changes), 'protected_files': len(protected)}))

if __name__ == '__main__':
    main()
