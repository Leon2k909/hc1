"""Stage just two well-water assets for guarded publication through the editor."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
revision = sys.argv[1]
folder = ROOT / 'output/belltower/well-water-v2' / revision
stage = folder / 'stage'
if stage.exists():
    raise SystemExit('Choose a fresh staging revision.')
sys.path.insert(0, str(ROOT / 'Tools'))
import belltower_well

hash_bytes = lambda data: hashlib.sha256(data).hexdigest()
assets = {
    'Assets/shaders/belltower_well_water_v2.shader': (ROOT / 'Sources/Belltower/well-water-v2/well_water.shader').read_bytes(),
    'Assets/materials/belltower/well-v1/well_water.vmat': belltower_well.material_definitions()[belltower_well.WATER].encode(),
}
manifest = {'files': {}}
for relative, data in assets.items():
    source = stage / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(data)
    target = ROOT / relative
    backup = folder / 'before' / relative
    before = None
    if target.exists():
        original = target.read_bytes()
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(original)
        before = hash_bytes(original)
    manifest['files'][relative] = dict(source=source.relative_to(ROOT).as_posix(),
        after=hash_bytes(data), before=before,
        backup=backup.relative_to(ROOT).as_posix() if before else None)
(stage / 'manifest.json').write_text(json.dumps(manifest, indent=2))
(folder.parent / 'import-request.json').write_text(json.dumps({'revision': revision}))
print(json.dumps(manifest))
