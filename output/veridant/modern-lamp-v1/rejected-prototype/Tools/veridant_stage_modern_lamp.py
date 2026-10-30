"""Stage the independent replacement fixture; does not change any map."""
import hashlib
import json
from pathlib import Path

import map_kit as K
import veridant_modern_lamp as L

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/veridant/modern-lamp-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stage = OUT / 'asset-stage-v1'
    assert not stage.exists(), 'Preserve earlier stages.'
    stage.mkdir()
    materials = stage / 'Assets/materials/veridant/modern-lamp-v1'
    L.write_materials(materials)
    model = K.Model()
    spec = L.build_into(model, (0, 0, 0))
    relative = Path('Assets/models/props/veridant/modern-lamp-v1')
    destination = stage / relative
    destination.mkdir(parents=True)
    K.write_obj(destination / 'bollard.obj', model, 'bollard')
    K.write_vmdl(destination / 'bollard.vmdl',
                 'models/props/veridant/modern-lamp-v1', 'bollard', model)
    files = {}
    for path in sorted((stage / 'Assets').rglob('*')):
        if not path.is_file():
            continue
        target = path.relative_to(stage).as_posix()
        assert not (ROOT / target).exists(), target
        files[target] = {'source': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)}
    manifest = {'revision': 'veridant-modern-lamp-asset-v1', 'files': files,
                'geometry': spec, 'triangles': model.triangle_count(),
                'collision_boxes': len(model.boxes), 'map_changes': False}
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'files': len(files), 'triangles': model.triangle_count(),
                      'map_changes': False}))


if __name__ == '__main__':
    main()
