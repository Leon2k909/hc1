"""Prepare a separate full-resolution canopy trial for native import.

No live assets are written. The accepted landscape and forest materials remain
the baseline; only new trial textures and two material copies are staged.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/belltower/quality/canopy-photo-v2-full'
TARGET = 'materials/belltower/vista/canopy-photo-v2'
ACCEPTED = ROOT/'Sources/Belltower/landscape/textures.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    trial = json.loads((STAGE/'trial.json').read_text())
    assert trial['style'] == 'photographic' and trial['size'] == 4096 and trial['zones'] == 'abcd'
    for path, digest in trial['sources'].items():
        assert sha(ROOT/path) == digest, 'Trial source changed: '+path
    accepted = json.loads(ACCEPTED.read_text())
    dependencies = dict(accepted['source_sha256'])
    for path in (
        'Assets/materials/belltower/forest/forest_trees.vmat',
        'Assets/materials/belltower/forest/forest-trees-v1.png',
        'Assets/shaders/hc1_vista.shader',
        'Assets/shaders/belltower_forest.shader',
    ):
        dependencies[path] = sha(ROOT/path)
    for path, digest in dependencies.items():
        assert sha(ROOT/path) == digest, 'Accepted dependency changed: '+path

    files, dimensions, unchanged_normals = [], {}, []
    landscape = (ROOT/'Assets/materials/belltower/vista/vista_land.vmat').read_text()
    forest = (ROOT/'Assets/materials/belltower/forest/forest_trees.vmat').read_text()
    for zone in 'abcd':
        normal = f'vista_{zone}_normal.jpg'
        assert sha(STAGE/normal) == dependencies['Assets/materials/belltower/vista/'+normal], 'Terrain normal changed: '+zone
        unchanged_normals.append(normal)
        for suffix in ('color.jpg', 'kind.png'):
            name = f'vista_{zone}_{suffix}'
            source = STAGE/name
            with Image.open(source) as image:
                assert image.size == (4096, 4096)
                assert image.mode == ('RGB' if suffix == 'color.jpg' else 'L')
                dimensions[name] = list(image.size)
            relative = TARGET+'/'+name
            original = 'materials/belltower/vista/'+name
            assert landscape.count('"'+original+'"') == 1
            landscape = landscape.replace('"'+original+'"', '"'+relative+'"')
            if suffix == 'color.jpg' and zone in 'bcd':
                assert forest.count('"'+original+'"') == 1
                forest = forest.replace('"'+original+'"', '"'+relative+'"')
            files.append((relative, source))

    for name, content in (('vista_land.vmat', landscape), ('forest_trees.vmat', forest)):
        source = STAGE/name
        source.write_text(content, encoding='utf-8', newline='\n')
        files.append((TARGET+'/'+name, source))

    payload = []
    for relative, source in files:
        destination = ROOT/'Assets'/relative
        digest = sha(source)
        assert not destination.exists() or sha(destination) == digest, 'A different trial is already installed: '+relative
        payload.append({'path':relative, 'source':source.relative_to(ROOT).as_posix(), 'sha256':digest,
                        'expected_sha256':digest if destination.exists() else None})
    sources = dict(trial['sources'])
    sources['Tools/belltower_quality_canopy.py'] = sha(Path(__file__))
    manifest = {
        'revision':'canopy-photo-v2', 'state':'staged for separate native comparison',
        'source_hashes':sources, 'base_inputs':dependencies,
        'accepted_manifest':{'path':ACCEPTED.relative_to(ROOT).as_posix(), 'sha256':sha(ACCEPTED)},
        'dimensions':dimensions, 'unchanged_normals':unchanged_normals, 'files':payload,
        'material_overrides':{
            'materials/belltower/vista/vista_land.vmat':TARGET+'/vista_land.vmat',
            'materials/belltower/forest/forest_trees.vmat':TARGET+'/forest_trees.vmat',
        },
        'scope':'Separate colour/kind textures and material copies only; no terrain, tree placement, model, shader, scene or accepted material is replaced.',
    }
    (STAGE/'native-import.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'trial_assets':len(payload), 'unchanged_normal_maps':len(unchanged_normals),
                      'native_import_pending':True}), flush=True)


if __name__ == '__main__':
    main()
