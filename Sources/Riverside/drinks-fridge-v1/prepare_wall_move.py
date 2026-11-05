"""Stage only the porch fridge's 64-inch translation and matching physics-box move."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/riverside/fridge-wall-placement-20261104"
MESH = "Assets/models/maps/riverside/drinks-fridge-v1/drinks_fridge.obj"
DOC = "Assets/models/maps/riverside/riverside_store.vmdl"
SCENE = "Assets/scenes/maps/Riverside/riverside.scene"
sha = lambda data: hashlib.sha256(data).hexdigest()
OUT.mkdir(parents=True, exist_ok=True)
before = {p: (ROOT / p).read_bytes() for p in (MESH, DOC, SCENE)}
for name, data in before.items():
    backup = OUT / "before-files" / name
    if backup.exists():
        assert backup.read_bytes() == data, "Placement baseline already exists with different files"
    else:
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(data)

vertices = 0
def translate(match):
    global vertices
    vertices += 1
    return match[1] + f"{float(match[2]) + 64:.3f}".encode() + match[3]

moved = re.sub(rb"^(v \S+ \S+ )([-\d.]+)(\r?\n)", translate, before[MESH], flags=re.M)
assert vertices > 0 and vertices == len(re.findall(rb"^v ", before[MESH], re.M))
old_box = b"origin = [ 560.0000, -96.0000, 56.0000 ]"
new_box = b"origin = [ 624.0000, -96.0000, 56.0000 ]"
assert before[DOC].count(old_box) == 1
files = {MESH: moved, DOC: before[DOC].replace(old_box, new_box)}
for name, data in files.items():
    target = OUT / "stage" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
plan = dict(before={p: sha(data) for p, data in before.items()}, files={p: sha(data) for p, data in files.items()},
            delta=[64, 0, 0], vertices=vertices, old_center=[560, -96, 56], new_center=[624, -96, 56],
            wall_x=640, rear_x=638, wall_gap=2,
            light_id="80b6490e-c7f9-5d88-b6e7-21cbf989ff0f", old_light=[534, -96, 63.2000008], new_light=[598, -96, 63.2000008])
(OUT / "move-plan.json").write_text(json.dumps(plan, indent=2))
print(json.dumps({k: v for k, v in plan.items() if k not in ("before", "files")}, indent=2))
