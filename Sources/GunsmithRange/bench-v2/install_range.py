"""Run gunsmith_range into a scratch folder and say what would change: python -X utf8 install_range.py <project root> <absolute scratch dir> [--copy]

The tool rewrites everything it owns, so nothing goes straight into Assets. The materials are left out, because the bench doesn't change them. The range's model files and the scene are compared,
the scene object by object, and with --copy the changed files go across only if each difference is one this change expects: the range's OBJ, MTL and VMDL, and four bench objects added.
Each file is written beside its target and moved over it, because the open editor can refuse a plain overwrite of a scene.
"""
import filecmp
import json
import os
import shutil
import sys
from pathlib import Path

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
COPY = "--copy" in sys.argv
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools"))
import gunsmith_range as G  # noqa: E402
import map_kit as K  # noqa: E402

live_models, live_scene = Path(G.OUT), K.ASSETS / "scenes/gunsmith_range.scene"
models = SCRATCH / "models/gunsmith_range"
models.mkdir(parents=True, exist_ok=True)
(SCRATCH / "scenes").mkdir(parents=True, exist_ok=True)
G.OUT = models
K.ASSETS = SCRATCH
G.materials = lambda: None
G.metadata = lambda path: None
sys.argv = ["gunsmith_range"]
G.main()

EXPECTED_FILES = {"gunsmith_range.obj", "gunsmith_range.mtl", "gunsmith_range.vmdl"}
changed, unexpected = [], []
for made in sorted(p for p in models.iterdir() if p.is_file()):
    live = live_models / made.name
    if not live.exists() or not filecmp.cmp(made, live, shallow=False):
        changed.append(made.name)
        if made.name not in EXPECTED_FILES:
            unexpected.append(made.name)
print("model files that differ:", changed)


def flat(objects):
    return {item.get("Name", "prefab") + "#" + item.get("__guid", ""): item for item in objects}


made_scene = SCRATCH / "scenes/gunsmith_range.scene"
old_root = json.loads(live_scene.read_bytes().decode("utf-8"))
new_root = json.loads(made_scene.read_bytes().decode("utf-8"))
old, new = flat(old_root["GameObjects"]), flat(new_root["GameObjects"])
added = sorted(set(new) - set(old))
removed = sorted(set(old) - set(new))
altered = sorted(k for k in set(old) & set(new) if old[k] != new[k])
properties = old_root.get("SceneProperties") != new_root.get("SceneProperties")
print("scene objects added:", [k.split("#")[0] for k in added])
print("scene objects removed:", [k.split("#")[0] for k in removed])
print("scene objects altered:", [k.split("#")[0] for k in altered])
print("scene properties differ:", properties)
for key in added:
    print("  ", new[key].get("Name"), new[key].get("Position"), [c.get("Model") for c in new[key]["Components"]])
if removed or altered or properties or (added and (len(added) != 4 or any(" m Bench" not in k for k in added))):
    unexpected.append("the scene differs by more than the benches")
print("unexpected:", unexpected)
if unexpected:
    sys.exit(1)
if COPY:
    for source, target in [(models / name, live_models / name) for name in changed] + ([(made_scene, live_scene)] if added else []):
        incoming = target.with_name(target.name + ".bench-incoming")
        shutil.copyfile(source, incoming)
        os.replace(incoming, target)
    print("copied:", changed, "and the scene" if added else "and not the scene")
