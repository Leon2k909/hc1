"""Reproduce Lowtide's private oak leaf resources from the accepted source inputs.

Use --out outside Assets for staging while the editor is open. Scene integration
is performed through the editor; no shared cloud tree asset is overwritten.
"""
from pathlib import Path
import argparse
import json
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Sources/Lowtide/foliage'
PREFIX = 'materials/lowtide/foliage-v2/'
MATERIAL = PREFIX + 'lt_oak_branch_v2.vmat'
SHADER = 'shaders/hc1_lowtide_foliage_v2.shader'
INPUTS = 'shaders/hc1_lowtide_foliage_v2_inputs.hlsl'
MODEL = 'models/sbox_props/trees/oak/tree_oak_medium_a.vmdl'
ORIGINAL_LEAF = 'models/sbox_props/trees/oak/oak_branch.vmat'


def resource_sources():
    result = {
        SHADER: SOURCE / 'production/hc1_lowtide_foliage_v2.shader',
        INPUTS: SOURCE / 'production/hc1_lowtide_foliage_v2_inputs.hlsl',
        MATERIAL: SOURCE / 'production/lt_oak_branch_v2.vmat',
        PREFIX + 'color.png': SOURCE / 'oak-branch-candidate-v2.png',
    }
    for name in ('coverage.png', 'normal.png', 'surface.png', 'transmission.png'):
        result[PREFIX + name] = SOURCE / 'native-inputs' / name
    return result


def write_assets(out):
    """Copy source bytes and stable metadata into an explicitly supplied asset root."""
    out = Path(out)
    written = []
    for relative, source in resource_sources().items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        written.append(target)
        if not relative.endswith('.hlsl'):
            guid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'hc1/lowtide/foliage-v2/' + relative))
            metadata = target.with_name(target.name + '.meta')
            metadata.write_bytes((json.dumps({'guid': guid}, indent=2) + '\n').encode())
            written.append(metadata)
    return written


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.resolve().is_relative_to(ROOT / 'Assets'), 'Import live resources through the editor'
    print(f'Staged {len(write_assets(args.out))} oak resource files.')
