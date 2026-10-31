"""Run boxyard_map into a scratch folder and say what would change: python install_map.py <project root> <scratch dir> [--copy]

The map script rewrites everything it owns, so nothing goes straight into Assets. Every model file and the scene are compared with what's there, the
scene object by object, so that other sessions' work can't be overwritten unseen. With --copy, the changed files are copied across, but only if each
difference is one this change expects. The radar picture never comes out identical, and the cones don't change it, so it stays as it is.
"""
import filecmp
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
COPY = "--copy" in sys.argv
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools"))
import boxyard_map as B  # noqa: E402

models = SCRATCH / "models"
models.mkdir(parents=True, exist_ok=True)
live_models, live_scene = Path(B.OUT_DIR), Path(B.SCENE_FILE)
B.OUT_DIR, B.SCENE_FILE, B.MINIMAP_FILE = models, SCRATCH / "boxyard.scene", SCRATCH / "minimap.png"
sys.argv = ["boxyard_map"]
B.main()

expected_models = {"boxyard_props.obj", "boxyard_props.vmdl", "boxyard_props.mtl", "boxyard_props_hulls_plastic.obj"}
changed, unexpected = [], []
for made in sorted(p for p in models.iterdir() if p.is_file()):
    live = live_models / made.name
    if not live.exists() or not filecmp.cmp(made, live, shallow=False):
        changed.append(made.name)
        if made.name not in expected_models:
            unexpected.append(made.name)
print("model files that differ:", changed)


def flat(objects, path=""):
    out = {}
    for item in objects:
        # A prefab instance has a guid but no name of its own.
        key = path + "/" + item.get("Name", "prefab") + "#" + item.get("__guid", "")
        out[key] = {k: v for k, v in item.items() if k != "Children"}
        out.update(flat(item.get("Children", []), key))
    return out


old = flat(json.loads(live_scene.read_text(encoding="utf-8"))["GameObjects"])
new = flat(json.loads((SCRATCH / "boxyard.scene").read_text(encoding="utf-8"))["GameObjects"])
added = sorted(set(new) - set(old))
removed = sorted(set(old) - set(new))
altered = sorted(k for k in set(old) & set(new) if old[k] != new[k])
print("scene objects added:", [k.split("/")[-1].split("#")[0] for k in added])
print("scene objects removed:", [k.split("/")[-1].split("#")[0] for k in removed])
print("scene objects altered:", [k.split("/")[-1].split("#")[0] for k in altered])
for key in added:
    print("  ", new[key].get("Name"), new[key].get("Position"), new[key].get("Rotation"))
if removed or altered or any("Cone" not in k.split("/")[-1] for k in added):
    unexpected.append("the scene differs by more than the cones")
if unexpected:
    print("NOT COPYING, unexpected:", unexpected)
    sys.exit(1)
if COPY:
    # Written beside each file and moved over it: the open editor can refuse a plain overwrite of a scene, which leaves the map half installed.
    for source, target in [(models / name, live_models / name) for name in changed] + [(SCRATCH / "boxyard.scene", live_scene)]:
        incoming = target.with_name(target.name + ".cone-incoming")
        shutil.copyfile(source, incoming)
        os.replace(incoming, target)
    print("copied:", changed, "and the scene")
    for path in [live_models / n for n in changed] + [live_scene]:
        print(hashlib.sha256(path.read_bytes()).hexdigest()[:16], path.name)
