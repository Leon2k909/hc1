"""Run orion_map into a scratch folder and say what would change: python install_map.py <project root> <scratch dir> <backup dir> [--copy]

Based on Boxyard's traffic_cone_v2. The map script rewrites everything it owns, so nothing goes straight into Assets. Every model file and the scene are compared with what's there, the scene object by object, so that
other sessions' work can't be overwritten unseen. With --copy, the changed files are backed up and moved across, but only if each difference is one this change expects.

Orion's OBJs don't come out identical even with no change to the script: on 2026-10-31, tiny corner triangles on five models' containers (rw_steel_dark) differed from the 17 October models, the same number but not the same corners.
So this doesn't take the script's OBJs. It takes each live OBJ and removes only the triangles of the crate's own materials that the script no longer draws: every other line stays as it was. Unused vertices stay too, which is harmless.
The radar picture doesn't change with these props, because the collision is the same, so it stays as it is.
"""
import filecmp
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT, SCRATCH, BACKUP = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
COPY = "--copy" in sys.argv
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools"))
import orion_map as B  # noqa: E402

CRATE_MODELS = ("orion_launch_control", "orion_launch_deck", "orion_props")
OTHER_OBJS = {"orion_courts.obj", "orion_pad.obj"}  # Differ only by those corners, and hold no crates. Left alone.
CRATE_MATERIALS = {"oa_red", "oa_dark", "oa_letters_light"}
CRATE_OBJECTS = {"Red crate"}
CRATE_TRIANGLES = 134  # At any size: read_old.py's count for one old crate.
CRATES_IN = {"orion_launch_control": 1, "orion_launch_deck": 5, "orion_props": 4}

B.STAGE = SCRATCH
models = SCRATCH / "Assets" / B.RESOURCE_DIR
models.mkdir(parents=True, exist_ok=True)
(SCRATCH / "Assets/scenes/maps/Orion").mkdir(parents=True, exist_ok=True)
(SCRATCH / "Assets" / B.MINIMAP_PATH).parent.mkdir(parents=True, exist_ok=True)
live_models, live_scene = B.ASSETS / B.RESOURCE_DIR, B.ASSETS / "scenes/maps/Orion/orion.scene"
made_scene = SCRATCH / "Assets/scenes/maps/Orion/orion.scene"
sys.argv = ["orion_map", "--stage"]
B.main()

changed, unexpected = [], []
for made in sorted(p for p in models.iterdir() if p.is_file()):
    live = live_models / made.name
    if made.suffix == ".obj" or (live.exists() and filecmp.cmp(made, live, shallow=False)):
        continue
    changed.append(made.name)
    # A model loses a material the crates alone used, and nothing else: its colliders are all still there.
    old_lines, new_lines = Counter(live.read_text(encoding="utf-8").splitlines()), Counter(made.read_text(encoding="utf-8").splitlines())
    lost = [line for line in (old_lines - new_lines) if not (made.suffix == ".mtl" and line.split()[0] in ("Kd", "d"))]
    if made.stem not in CRATE_MODELS or new_lines - old_lines and made.suffix != ".mtl" or not all(any(m in line for m in CRATE_MATERIALS) for line in lost):
        unexpected.append(made.name)
for made in sorted(models.glob("*.obj")):
    live = live_models / made.name
    if made.stem not in CRATE_MODELS and made.name not in OTHER_OBJS and not filecmp.cmp(made, live, shallow=False):
        unexpected.append(made.name)
print("non-OBJ model files that differ:", changed)


def triangles(path):
    """Each line of an OBJ's crate-material triangles as its real corners: the two files number their vertices differently."""
    pos, tex, nor, out, material = [], [], [], [], None
    for number, line in enumerate(open(path, encoding="utf-8")):
        tag = line[:2]
        if tag == "v ":
            pos.append(line)
        elif tag == "vt":
            tex.append(line)
        elif tag == "vn":
            nor.append(line)
        elif line.startswith("usemtl"):
            material = line.split()[1]
        elif tag == "f " and material in CRATE_MATERIALS:
            corners = [tok.split("/") for tok in line.split()[1:]]
            out.append((number, material, tuple((pos[int(c[0]) - 1], tex[int(c[1]) - 1], nor[int(c[2]) - 1]) for c in corners)))
    return out


for name in CRATE_MODELS:
    live_path, made_path = live_models / f"{name}.obj", models / f"{name}.obj"
    live_faces = triangles(live_path)
    keep = Counter((material, corners) for _, material, corners in triangles(made_path))
    gone = {}
    for number, material, corners in live_faces:
        if keep[(material, corners)] > 0:
            keep[(material, corners)] -= 1
        else:
            gone[number] = material
    extra = sum(keep.values())
    print(f"{name}: {len(gone)} of {len(live_faces)} crate-material triangles removed, by material {dict(Counter(gone.values()))}; {extra} the script has that the live model doesn't")
    # Each old crate is 134 triangles.
    if extra or len(gone) != CRATE_TRIANGLES * CRATES_IN[name]:
        unexpected.append(f"{name}'s triangles")
    left = Counter(material for _, material, _ in live_faces) - Counter(gone.values())
    with open(live_path, encoding="utf-8", newline="") as source, open(made_path.with_suffix(".cut"), "w", encoding="utf-8", newline="") as out:
        for number, line in enumerate(source):
            # A material with nothing left loses its heading too, as the map script's own file does.
            if number not in gone and not (line.startswith("usemtl") and line.split()[1] in CRATE_MATERIALS and not left[line.split()[1]]):
                out.write(line)


def flat(objects, path=""):
    out = {}
    for item in objects:
        # A prefab instance has a guid but no name of its own.
        key = path + "/" + item.get("Name", "prefab") + "#" + item.get("__guid", "")
        out[key] = {k: v for k, v in item.items() if k != "Children"}
        out.update(flat(item.get("Children", []), key))
    return out


old = flat(json.loads(live_scene.read_text(encoding="utf-8"))["GameObjects"])
new = flat(json.loads(made_scene.read_text(encoding="utf-8"))["GameObjects"])
added = sorted(set(new) - set(old))
removed = sorted(set(old) - set(new))
altered = sorted(k for k in set(old) & set(new) if old[k] != new[k])
print("scene objects added:", [k.split("/")[-1].split("#")[0] for k in added])
print("scene objects removed:", [k.split("/")[-1].split("#")[0] for k in removed])
print("scene objects altered:", [k.split("/")[-1].split("#")[0] for k in altered])
for key in added:
    print("  ", new[key].get("Name"), new[key].get("Position"), new[key].get("Rotation"), new[key].get("Scale"))
if removed or altered or any(new[k].get("Name") not in CRATE_OBJECTS for k in added):
    unexpected.append("the scene differs by more than the crates")
if unexpected:
    print("NOT COPYING, unexpected:", unexpected)
    sys.exit(1)
if COPY:
    BACKUP.mkdir(parents=True, exist_ok=True)
    pairs = [(models / f"{name}.cut", live_models / f"{name}.obj") for name in CRATE_MODELS] + [(models / name, live_models / name) for name in changed] + [(made_scene, live_scene)]
    # Written beside each file and moved over it: the open editor can refuse a plain overwrite of a scene, which leaves the map half installed.
    for source, target in pairs:
        shutil.copyfile(target, BACKUP / target.name)
        incoming = target.with_name(target.name + ".install-incoming")
        shutil.copyfile(source, incoming)
        os.replace(incoming, target)
    print("copied:")
    for _, target in pairs:
        print(hashlib.sha256(target.read_bytes()).hexdigest()[:16], target.name)
