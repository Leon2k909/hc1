"""Check the installed floor against the captured public input and staged output."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/ares/floor-live-v4'
sys.path.insert(0, str(ROOT / 'Tools'))
import riverdale_splice as splice

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

plan = json.loads((OUT / 'install-plan.json').read_text())
for rel, expected in plan['files'].items():
    assert sha(ROOT / rel) == expected, f'Installed file differs: {rel}'
for rel, expected in plan['guards'].items():
    if rel not in plan['files']:
        assert sha(ROOT / rel) == expected, f'Unrelated input changed: {rel}'
model = 'Assets/models/maps/ares/ares_hall.vmdl'
before = (OUT / 'before' / model).read_text()
after = (ROOT / model).read_text()
assert after == before.replace('materials/ares/interior-v1/floor.vmat', 'materials/ares/floor-finish-v4/plate.vmat').replace('materials/ares/ar_floor.vmat', 'materials/ares/floor-finish-v4/grip.vmat')
obj = 'Assets/models/maps/ares/pressure-doors-v2/hall_base.obj'
old_faces = splice.read_obj(OUT / 'before' / obj)[1]
new_faces = splice.read_obj(ROOT / obj)[1]
removed = Counter(splice.read_obj(OUT / 'removed.obj')[1])
added = Counter(splice.read_obj(OUT / 'added.obj')[1])
old_retained = Counter(old_faces) - removed
new_retained = Counter(new_faces) - added
assert Counter(f for f in old_retained.elements() if f[0] != 'ar_floor') == Counter(f for f in new_retained.elements() if f[0] != 'ar_floor')
def without_uv(faces):
    return Counter((paint, tuple((p, normal) for p, uv, normal in corners)) for paint, corners in faces if paint == 'ar_floor')
assert without_uv(old_retained.elements()) == without_uv(new_retained.elements())
for rel in plan['files']:
    if rel.endswith('.py'):
        compile((ROOT / rel).read_text(), rel, 'exec')
report = dict(InstalledHashesMatch=True, SceneUnchanged=True, CollisionUnchanged=True,
              OtherGeometryPreserved=True, GeneratorSyntaxValid=True,
              HallTriangles=len(new_faces), ReplacedFloorTriangles=sum(removed.values()),
              NewFloorTriangles=sum(added.values()))
(OUT / 'verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
