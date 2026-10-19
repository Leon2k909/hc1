"""Snapshot and stage only the six reviewed Lowtide material definitions."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import lowtide_container_surface as surface

FOLDER = ROOT / 'output/lowtide/quality-pass/container-surface'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = json.loads((FOLDER / 'manifest.json').read_text())
preview = json.loads((FOLDER / 'native-preview.json').read_text())
assert len(preview['captures']) == 8 and preview['overridesRestored']
assert not preview['HasUnsavedChanges'] and not preview['IsPlaying']
for relative, expected in manifest['protected'].items():
    assert digest(ROOT / relative) == expected, relative
for relative, values in manifest['changes'].items():
    assert digest(ROOT / 'Assets' / relative) == values['after'], relative
assert not (FOLDER / 'production-manifest.json').exists(), 'Inspect existing promotion before retrying'
changes = {}
for colour in ('blue', 'red', 'grey'):
    for frame in (False, True):
        name = f'lt_container_{colour}' + ('_frame' if frame else '') + '.vmat'
        relative = 'materials/lowtide/containers/' + name
        live = ROOT / 'Assets' / relative
        stage = FOLDER / 'production-stage' / relative
        before = FOLDER / 'before' / relative
        stage.parent.mkdir(parents=True, exist_ok=True)
        before.parent.mkdir(parents=True, exist_ok=True)
        before.write_bytes(live.read_bytes())
        stage.write_bytes(surface.material_text(colour, frame).encode('utf-8'))
        candidate = ROOT / 'Assets/materials/lowtide/container_surface' / name
        assert stage.read_bytes() == candidate.read_bytes()
        changes[relative] = {'before': digest(live), 'after': digest(stage)}
protected = {relative: sha for relative, sha in manifest['protected'].items()
             if relative.removeprefix('Assets/') not in changes}
protected.update({'Assets/' + relative: item['after'] for relative, item in manifest['changes'].items()})
report = {'changes': changes, 'protected': protected,
          'scope': 'Six material definitions only. Generated paint pixels, mesh, collision, scene, lighting and metadata unchanged.',
          'visual_review': 'Four before/candidate pairs reviewed: modest paint response, top-seam dirt and lower-rail weathering accepted.'}
(FOLDER / 'production-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'staged_materials': len(changes), 'protected_files': len(protected)}))
