"""Run reefhall_map into a scratch folder and say what would change: python -X utf8 install_map.py <project root> <absolute scratch dir inside the project> [--copy]

The map script rewrites everything it owns, so nothing goes straight into Assets. Every model file and the scene are compared, the scene object by object, and with --copy the
changed files go across only if each difference is one the stands expect: the rotunda's and tunnel's models, and three new objects in the scene. Each file is written beside its target
and moved over it, because the open editor can refuse a plain overwrite of a scene. The radar picture, the materials and the tank materials are left as they are: the stands don't change them.
"""
import filecmp
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
COPY = "--copy" in sys.argv
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools"))
import reefhall_map as B  # noqa: E402

models = SCRATCH / "models"
models.mkdir(parents=True, exist_ok=True)
live_models, live_scene = Path(B.OUT_DIR), Path(B.SCENE_FILE)
B.OUT_DIR, B.SCENE_FILE, B.MINIMAP_FILE = models, SCRATCH / live_scene.name, SCRATCH / "minimap.png"
B.write_tank_materials = lambda: None
sys.argv = ["reefhall_map"]
B.main()

ROOMS_WITH_STANDS = ("reefhall_rotunda", "reefhall_tunnel")
changed, unexpected = [], []
for made in sorted(p for p in models.iterdir() if p.is_file()):
    live = live_models / made.name
    if not live.exists() or not filecmp.cmp(made, live, shallow=False):
        changed.append(made.name)
        if not made.name.startswith(ROOMS_WITH_STANDS) or "_tanks" in made.name:
            unexpected.append(made.name)
print("model files that differ:", changed)


def flat(objects, path=""):
    out = {}
    for item in objects:
        key = path + "/" + item.get("Name", "prefab") + "#" + item.get("__guid", "")
        out[key] = {k: v for k, v in item.items() if k != "Children"}
        out.update(flat(item.get("Children", []), key))
    return out


old = flat(json.loads(live_scene.read_bytes().decode("utf-8"))["GameObjects"])
new = flat(json.loads(B.SCENE_FILE.read_bytes().decode("utf-8"))["GameObjects"])
added = sorted(set(new) - set(old))
removed = sorted(set(old) - set(new))
altered = sorted(k for k in set(old) & set(new) if old[k] != new[k])
print("scene objects added:", [k.split("/")[-1].split("#")[0] for k in added])
print("scene objects removed:", [k.split("/")[-1].split("#")[0] for k in removed])
print("scene objects altered:", [k.split("/")[-1].split("#")[0] for k in altered])
for key in added:
    print("  ", new[key].get("Name"), new[key].get("Position"), new[key].get("Rotation"))
if removed or altered or len(added) != 3 or any(" Stand " not in k.split("/")[-1] for k in added):
    unexpected.append("the scene differs by more than the stands")
if unexpected:
    print("NOT COPYING, unexpected:", unexpected)
    sys.exit(1)
if COPY:
    # The open editor compiles each file as it lands and holds it meanwhile, which refused a move and left the map half installed: so wait for it.
    for source, target in [(models / name, live_models / name) for name in changed] + [(B.SCENE_FILE, live_scene)]:
        incoming = target.with_name(target.name + ".stand-incoming")
        shutil.copyfile(source, incoming)
        for attempt in range(60):
            try:
                os.replace(incoming, target)
                break
            except PermissionError:
                time.sleep(2)
        else:
            raise SystemExit(f"{target} stayed locked: rerun this, as the map is half installed.")
    print("copied:", changed, "and the scene")
