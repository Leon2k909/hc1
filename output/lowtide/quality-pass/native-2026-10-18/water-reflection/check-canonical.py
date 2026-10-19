"""Check current integration against the reviewed native candidate without writing Assets."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tools'))
import lowtide_water_filter as F
import lowtide_water as W

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = json.loads((OUT / 'manifest.json').read_text())
capture = (ROOT / F.CODE).read_text()
assert F.code((OUT / 'before' / F.CODE).read_text()) == capture
assert F.code() == capture
assert F.shader() == (ROOT / F.SHADER).read_text()
assert F.material((OUT / 'before' / F.MATERIAL).read_text()) == (ROOT / F.MATERIAL).read_text()
assert F.material((ROOT / F.MATERIAL).read_text()) == (ROOT / F.MATERIAL).read_text()

# Exercise the canonical writer while redirecting writes to memory.
written = {}
W.K.write_text = lambda p, text: written.__setitem__(Path(p).resolve(), text)
W.bake_wave_normals = lambda: None
W.write_materials()
assert set(written) == {ROOT / F.MATERIAL, ROOT / F.SHADER}
for path, text in written.items():
    assert text == path.read_text(), path

protected = [F.BASE_SHADER, 'Assets/models/maps/lowtide/lowtide_water.vmdl',
             'Assets/models/maps/lowtide/lowtide_water.obj', 'Assets/scenes/maps/Lowtide/lowtide.scene']
assert all(sha(ROOT / p) == manifest['sources'][p] for p in protected)
for p in [ROOT / 'Tools/lowtide_water.py', ROOT / 'Tools/lowtide_water_filter.py']:
    ast.parse(p.read_text(), filename=str(p))
report = dict(capture_reproduced=True, capture_idempotent=True, shader_reproduced=True,
              canonical_writer_reproduced=True, material_idempotent=True,
              protected_unchanged=protected, assets_written=False,
              installed={p: sha(ROOT / p) for p in [F.CODE, F.MATERIAL, F.SHADER, F.SHADER + '.meta']},
              generators={p: sha(ROOT / p) for p in ['Tools/lowtide_water.py', 'Tools/lowtide_water_filter.py']})
(OUT / 'canonical-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
