"""Stage the reviewed 90%-parcel Belltower terrain as isolated native assets.

Run after belltower_vista_paint.py wrote ALL 4 high-resolution zones to
output/belltower/quality/parcel-v4-production. Source collision, old terrain,
near trees and forest remain untouched until a native comparison is accepted.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image

import belltower_vista_paint as P

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/belltower/quality/parcel-v4-production'
RESOURCE = 'materials/belltower/vista/parcel-v4'
SOURCE = ROOT / 'Assets/materials/belltower/vista'
FOREST_SOURCE = ROOT / 'Assets/materials/belltower/forest/forest_trees.vmat'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage():
    if P.PARCEL != 5580.0:
        raise RuntimeError(f'Expected accepted 90% parcel scale (5580), got {P.PARCEL}')
    if not STAGE.is_dir():
        raise RuntimeError('Missing full-resolution landscape staging directory')
    source = FOREST_SOURCE.read_text(encoding='utf-8')
    for zone in 'bcd':
        for kind in ('color.jpg', 'normal.jpg'):
            old = f'materials/belltower/vista/vista_{zone}_{kind}'
            new = f'{RESOURCE}/vista_{zone}_{kind}'
            assert source.count('"'+old+'"') == 1, old
            source = source.replace('"'+old+'"', '"'+new+'"')
    (STAGE / 'forest_trees.vmat').write_text(source, encoding='utf-8', newline='\n')
    files = []
    dimensions = {}
    unchanged = {}
    manifest_expected = json.loads((ROOT / 'Sources/Belltower/landscape/textures.json').read_text())['source_sha256']
    for zone in 'abcd':
        for kind in ('color.jpg', 'kind.png', 'normal.jpg'):
            name = f'vista_{zone}_{kind}'
            stage_path = STAGE / name
            old_path = SOURCE / name
            resolution = (2048, 2048) if kind == 'normal.jpg' else (4096, 4096)
            with Image.open(stage_path) as image:
                if image.size != resolution:
                    raise RuntimeError(f'{name}: unexpected resolution {image.size}')
            with Image.open(old_path) as image:
                assert image.size == resolution
            old_key = old_path.relative_to(ROOT).as_posix()
            if sha(old_path) != manifest_expected[old_key]:
                raise RuntimeError(f'Accepted asset has changed since the previous landscape: {old_key}')
            unchanged[old_key] = sha(old_path)
            dimensions[name] = list(resolution)
            files.append(stage_path)
    for kind in ('grass', 'soil', 'stone'):
        name = f'detail_{kind}.png'
        with Image.open(STAGE / name) as image:
            assert image.size == (1024, 1024)
        dimensions[name] = [1024, 1024]
        unchanged[(SOURCE / name).relative_to(ROOT).as_posix()] = sha(SOURCE / name)
        files.append(STAGE / name)
    for name in ('vista_land.vmat', 'forest_trees.vmat'):
        assert (STAGE / name).is_file()
        files.append(STAGE / name)
    unchanged[(SOURCE / 'vista_land.vmat').relative_to(ROOT).as_posix()] = sha(SOURCE / 'vista_land.vmat')
    unchanged[FOREST_SOURCE.relative_to(ROOT).as_posix()] = sha(FOREST_SOURCE)
    unchanged['Assets/scenes/maps/Belltower/belltower.scene'] = sha(ROOT / 'Assets/scenes/maps/Belltower/belltower.scene')
    unchanged['Sources/Belltower/landscape/trees.json'] = sha(ROOT / 'Sources/Belltower/landscape/trees.json')
    unchanged['Sources/Belltower/landscape/forest.json'] = sha(ROOT / 'Sources/Belltower/landscape/forest.json')
    payload = []
    for path in files:
        relative = RESOURCE + '/' + path.name
        target = ROOT / 'Assets' / relative
        if target.exists() and sha(target) != sha(path):
            raise RuntimeError('Conflicting trial resource: '+relative)
        payload.append({'path': relative, 'source': path.relative_to(ROOT).as_posix(),
                        'sha256': sha(path),
                        'existing_sha256': sha(target) if target.exists() else None})
    output = {
        'revision': 'parcel-v4', 'stage': 'native visual comparison; original assets unchanged',
        'parcel': 5580.0, 'original_parcel': 6200.0,
        'generator_path': 'Tools/belltower_vista_paint.py',
        'generator_sha256': sha(ROOT / 'Tools/belltower_vista_paint.py'),
        'source_sha256': unchanged,
        'resources': payload,
        'dimensions': dimensions,
        'colliders_changed': False,
        'material_overrides': {
            'materials/belltower/vista/vista_land.vmat': RESOURCE+'/vista_land.vmat',
            'materials/belltower/forest/forest_trees.vmat': RESOURCE+'/forest_trees.vmat',
        },
    }
    (STAGE / 'native-trial-manifest.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'native_resources': len(files), 'dimensions': len(dimensions),
                      'accepted_inputs': len(unchanged), 'material_overrides': 2}, indent=2))


if __name__ == '__main__':
    stage()
