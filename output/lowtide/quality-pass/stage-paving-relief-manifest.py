from pathlib import Path
import hashlib
import json
import uuid

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'output/lowtide/quality-pass'
STAGE = FOLDER / 'paving-relief-stage'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

files = sorted(p for p in STAGE.rglob('*') if p.suffix in ('.png', '.vmat', '.shader'))
for path in files:
    relative = path.relative_to(STAGE).as_posix()
    meta = Path(str(path) + '.meta')
    if not meta.exists():
        meta.write_text(json.dumps({'guid': str(uuid.uuid5(uuid.NAMESPACE_URL, relative))}, indent=2) + '\n')
files = sorted(p for p in STAGE.rglob('*') if p.suffix in ('.png', '.vmat', '.shader', '.meta'))
changes = {}
for path in files:
    relative = path.relative_to(STAGE).as_posix()
    live = ROOT / 'Assets' / relative
    assert not live.exists(), f'Candidate already imported: inspect before retrying {relative}'
    changes[relative] = {'before': None, 'after': sha(path)}
protected = sorted(set(
    list((ROOT / 'Assets/models/maps/lowtide').glob('*.obj'))
    + list((ROOT / 'Assets/models/maps/lowtide').glob('*.vmdl'))
    + list((ROOT / 'Assets/models/maps/lowtide').glob('*.mtl'))
    + list((ROOT / 'Assets/scenes/maps/Lowtide').glob('*.scene'))
    + list((ROOT / 'Assets/materials/lowtide').glob('lt_setts*'))
    + [ROOT / 'Tools/lowtide_paving_source.png', ROOT / 'Tools/lowtide_paving_imagegen.json',
       ROOT / 'Assets/shaders/hc1_lowtide_paving.shader']))
protected = [p for p in protected if p.is_file() and not p.name.endswith('_c')]
manifest = dict(changes=changes, protected={p.relative_to(ROOT).as_posix(): sha(p) for p in protected},
    status='staged candidate only; import and visual comparison pending',
    surface_report=json.loads((STAGE/'surface-report.json').read_text()))
(FOLDER / 'paving-relief-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'new_files': len(changes), 'protected_files': len(protected), 'status': manifest['status']}))
