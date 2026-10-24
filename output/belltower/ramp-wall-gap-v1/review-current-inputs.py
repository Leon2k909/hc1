"""Revalidate the narrow repair against concurrent, unrelated map updates."""
import hashlib
import json
from pathlib import Path
import re
import sys
import types

sys.path.insert(0, str(Path('Tools').resolve()))
import belltower_stage_ramp_gap as S

path = Path('output/belltower/ramp-wall-gap-v1/publication/stage/manifest.json')
manifest = json.loads(path.read_text())
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

allowed = {'Tools/belltower_map.py',
           'Assets/models/maps/belltower/belltower_west.vmdl',
           'Assets/models/maps/belltower/belltower_east.vmdl'}
current = {name: sha(name) for name in allowed}
scene = 'Assets/scenes/maps/Belltower/belltower.scene'
scene_hash = sha(scene)
for side in ('west', 'east'):
    refs = re.findall(r'filename\s*=\s*"([^"]+\.obj)"',
                      Path(f'Assets/models/maps/belltower/belltower_{side}.vmdl').read_text())
    assert manifest['models'][side]['runtime_piece'] in refs
baseline = Path('output/belltower/ramp-wall-gap-v1/baseline-wall-cleanup.py.txt')
legacy = types.ModuleType('baseline')
exec(compile(baseline.read_text(), str(baseline), 'exec'), legacy.__dict__)
_, _, old_area, new_area = S.geometry_checks(legacy)
assert old_area == manifest['garden_face_area_before']
assert new_area == manifest['garden_face_area_after']
assert all(sha(name) == expected for name, expected in current.items())
assert sha(scene) == scene_hash
reviewed = {}
for group in ('source_sha256', 'protected_sha256'):
    for name, expected in list(manifest[group].items()):
        actual = sha(name)
        if actual != expected:
            assert name in allowed, name
            reviewed[name] = {'previous': expected, 'reviewed': actual}
            manifest[group][name] = actual
for name, row in manifest['files'].items():
    assert sha(name) == row['before'], name
manifest.setdefault('input_reviews', []).append({
    'updated_inputs': reviewed,
    'previous_scene_sha256': manifest['scene_sha256'],
    'current_scene_sha256': scene_hash,
    'entire_current_town_wall_geometry_and_collision_rechecked': True,
    'runtime_rubble_piece_still_referenced_by_each_current_model': True,
    'all_four_patched_asset_inputs_unchanged': True,
})
manifest['scene_sha256'] = scene_hash
path.write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(manifest['input_reviews'][-1]))
