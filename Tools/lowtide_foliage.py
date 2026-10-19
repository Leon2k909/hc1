"""Stage a Lowtide-only oak material candidate; never alter shared cloud trees."""
from pathlib import Path
import argparse
import hashlib
import json
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Sources/Lowtide/foliage'
SHADER = 'shaders/hc1_lowtide_foliage.shader'
INPUTS = 'shaders/hc1_lowtide_foliage_inputs.hlsl'
ATLAS = 'materials/lowtide/foliage/lt_oak_branch_color.png'
MATERIAL = 'materials/lowtide/foliage/lt_oak_branch.vmat'

def material_text():
    return f'''// Tools/lowtide_foliage.py: generated oak atlas; private Lowtide candidate.
"Layer0"
{{
    shader "{SHADER}"
    F_ALPHA_TEST "1"
    F_RENDER_BACKFACES "1"
    F_FOLIAGE_ANIMATION "1"
    F_TRANSMISSIVE "1"
    F_GRAZING_FADE "1"
    TextureColor "{ATLAS}"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "[0.75 0.75 0.75 0]"
    TextureMetalness "[0 0 0 0]"
    TextureBlendMask "[0 0 0 0]"
    TextureAmbientOcclusion "[1 1 1 0]"
    TextureTransmissiveColor "{ATLAS}"
    g_flTintColor "[1 1 1]"
    g_flAlphaTestReference ".42"
    g_flAlphaDistanceStart "800"
    g_flAlphaDistanceEnd "2800"
    g_flAntiAliasedEdgeStrength "1"
    g_flWrapAmount ".4"
    g_flWrapStrength ".3"
    g_flTransmissionScale "1.8"
    g_flAmbientBoost "0"
    g_flRimStrength "0"
    g_flMinRoughness ".75"
    g_flNormalVariation ".06"
    g_flGrassNormalUp ".22"
    g_flGrazingFadeStart ".20"
    g_flGrazingFadeEnd ".03"
    g_flEdgeFrequency ".1"
    g_flEdgeAmplitude "0"
    g_flBranchFrequency "3.171"
    g_flBranchAmplitude "1"
    g_flSwayStrength "25"
    g_flSwaySpeed "1"
}}
'''

def stage(out):
    out = out.resolve()
    assert not out.is_relative_to(ROOT / 'Assets'), 'Stage outside live assets'
    manifest_path = out.parent / 'candidate-manifest.json'
    assert not manifest_path.exists(), 'Inspect an existing candidate before replacing its manifest'
    changes = {}
    def put(relative, data, metadata=True):
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        changes[relative] = hashlib.sha256(data).hexdigest()
        if metadata:
            meta = json.dumps({'guid': str(uuid.uuid5(uuid.NAMESPACE_URL, 'hc1/lowtide/foliage/' + relative))}, indent=2).encode() + b'\n'
            put(relative + '.meta', meta, False)
    put(SHADER, (SOURCE / 'hc1_lowtide_foliage.shader').read_bytes())
    put(INPUTS, (SOURCE / 'hc1_lowtide_foliage_inputs.hlsl').read_bytes(), False)
    put(ATLAS, (SOURCE / 'oak-branch-candidate.png').read_bytes())
    put(MATERIAL, material_text().encode())
    protected = {}
    for directory in ('Assets/materials/lowtide', 'Assets/models/maps/lowtide', 'Assets/scenes/maps/Lowtide'):
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and not path.name.endswith('_c'):
                protected[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for relative in ('models/sbox_props/trees/oak/tree_oak_medium_a.vmdl_c',
                     'models/sbox_props/trees/oak/oak_branch.vmat_c', 'models/sbox_props/trees/oak/oak_bark.vmat_c'):
        path = ROOT / '.sbox/cloud' / relative
        protected[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps({'changes': changes, 'protected': protected,
        'status': 'Unused candidate staged. Scene and all four shared tree references retained.'}, indent=2) + '\n')
    print(json.dumps({'candidate_files': len(changes), 'protected_files': len(protected)}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    stage(parser.parse_args().stage)
