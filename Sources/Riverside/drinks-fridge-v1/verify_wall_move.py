"""Verify the installed porch-fridge placement against its pre-move files and native ray receipt."""
from pathlib import Path
import hashlib
import json
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/riverside/fridge-wall-placement-20261104"
plan = json.loads((OUT / "move-plan.json").read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
for name, expected in plan["files"].items():
    assert sha((ROOT / name).read_bytes()) == expected, f"Installed file differs: {name}"
mesh_name = "Assets/models/maps/riverside/drinks-fridge-v1/drinks_fridge.obj"
doc_name = "Assets/models/maps/riverside/riverside_store.vmdl"
scene_name = "Assets/scenes/maps/Riverside/riverside.scene"
before_mesh = (OUT / "before-files" / mesh_name).read_bytes().splitlines()
after_mesh = (ROOT / mesh_name).read_bytes().splitlines()
assert len(before_mesh) == len(after_mesh)
for old, new in zip(before_mesh, after_mesh):
    if old.startswith(b"v "):
        assert np.allclose(np.array(new.split()[1:], float) - np.array(old.split()[1:], float), (0, 0, 64), atol=1e-6)
    else:
        assert old == new, "Non-position mesh record changed"
old_doc = (OUT / "before-files" / doc_name).read_bytes()
new_doc = (ROOT / doc_name).read_bytes()
assert old_doc.replace(b"origin = [ 560.0000, -96.0000, 56.0000 ]", b"origin = [ 624.0000, -96.0000, 56.0000 ]") == new_doc

before_scene = json.loads((OUT / "before-files" / scene_name).read_text())
after_scene = json.loads((ROOT / scene_name).read_text())
def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))
old_light = next(x for x in walk(before_scene["GameObjects"]) if x["__guid"] == plan["light_id"])
new_light = next(x for x in walk(after_scene["GameObjects"]) if x["__guid"] == plan["light_id"])
assert np.allclose(np.fromstring(new_light["Position"], sep=","), plan["new_light"])
new_light["Position"] = old_light["Position"]
assert before_scene == after_scene, "Scene changed beyond the porch-fridge light position"

# Exercise only the prop hook, never the full map generator.
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverside_drinks_fridge as fridge
generated = fridge.model()
expected = OUT / "generated" / "drinks_fridge.obj"
expected.parent.mkdir(exist_ok=True)
K.write_obj(expected, generated, "drinks_fridge")
def vertices(path):
    return np.array([line.split()[1:] for line in path.read_text().splitlines() if line.startswith("v ")], float)
assert np.array_equal(vertices(expected), vertices(ROOT / mesh_name)), "Prop generator geometry differs from installed fridge"
hook = K.Model()
fridge.append_to(hook)
assert len(hook.boxes) == 1 and np.allclose(K.to_world(hook.boxes[0][0]), plan["new_center"])

native = json.loads((OUT / "native-validation.json").read_text())
rays = {x["Label"]: x for x in native["Rays"]}
assert not native["ModelError"] and native["SceneUnchanged"] and not native["Unsaved"]
assert not rays["old cabinet footprint"]["Hit"] and not rays["store doorway"]["Hit"]
for name, position in (("moved cabinet front", (610, -96, 56)), ("wall behind cabinet", (640, -96, 56)), ("cabinet rear", (638, -96, 56))):
    hit = rays[name]
    assert hit["Hit"] and np.allclose(np.fromstring(hit["HitPosition"], sep=","), position)
report = dict(fridges_moved=1,shift_inches=64,wall_gap_inches=2,mesh_positions_only=True,other_physics_unchanged=True,
              scene_light_only=True,generator_matches_installed=True,old_footprint_clear=True,doorway_clear=True,
              compiled_model_valid=True,native_rays_passed=5,live_gameplay_checked=False)
(OUT / "verified.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
