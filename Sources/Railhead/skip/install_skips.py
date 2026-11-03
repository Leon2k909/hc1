"""Swap Railhead's two yard skips for Lowtide's without regenerating the map: python install_skips.py <project root> [--write]

The old skips are merged into the dress models, and railhead_dress_east and _west build from extinguisher-v2/east-base.obj and west-base.obj, so the cut goes there as well as in the generator's OBJs. This builds each old skip with the map's own numbers.
Every corner of a cut face must be one of that skip's, and each file must lose exactly its triangles, or nothing is written. Its collision box comes out of the live vmdl too, because the new model brings its own, open inside.
Then it writes the model and adds a "Skips" group to the scene, which is what railhead_skips.scene_group() makes on a full run. Without --write it only reports. An open editor recompiles the models by itself.
A file that's already been cut is left alone, so a run the editor interrupted can be run again: it holds an OBJ open while it compiles, so each replace is retried for a few minutes.
"""
import json
import os
import pathlib
import sys
import tempfile
import time

import numpy as np
from scipy.spatial import cKDTree

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import railhead_dress_detail as D  # noqa: E402
import railhead_map as M  # noqa: E402
import railhead_skips as S  # noqa: E402

DIR = os.path.join(ROOT, "Assets", "models", "maps", "railhead")
FILES = {-1.0: ("extinguisher-v2/west-base.obj", "railhead_dress_west.obj"), 1.0: ("extinguisher-v2/east-base.obj", "railhead_dress_east.obj")}
VMDLS = {-1.0: "railhead_dress_west.vmdl", 1.0: "railhead_dress_east.vmdl"}
PAINTS = {"rw_yellow_paint", "rw_steel_dark", "rw_ballast_old"}
OLD_E, NEW_E, N = 2158.0, 2155.0, -1575.0

out = {}
placed = []
for s, names in FILES.items():
    model = K.Model()
    D.skip_bin_old(model, s * OLD_E, N, "+n")
    for paint in model.polygons:
        model.tile_overrides[paint] = 64.0
    with tempfile.TemporaryDirectory() as scratch:
        target = pathlib.Path(scratch) / "old_skip.obj"
        K.write_obj(target, model, "old_skip")
        text = open(target, encoding="utf-8").read().splitlines()
    old = np.array([line[2:].split()[:3] for line in text if line.startswith("v ")], float)[:, [2, 0, 1]]
    old_triangles = sum(len(line.split()) - 3 for line in text if line.startswith("f "))
    corners = cKDTree(old)
    low, high = old.min(0) - 1, old.max(0) + 1
    print("side", s, "old skip:", old_triangles, "triangles, paints", sorted(model.polygons), flush=True)
    for name in names:
        path = os.path.join(DIR, name)
        with open(path, encoding="utf-8", newline="") as h:
            lines = h.readlines()
        v = np.array([line[2:].split()[:3] for line in lines if line.startswith("v ")], float)[:, [2, 0, 1]]
        current = None
        drop = set()
        count = 0
        for number, line in enumerate(lines):
            if line.startswith("usemtl"):
                current = line.split()[1]
            elif line.startswith("f ") and current in PAINTS:
                tokens = line.split()[1:]
                q = v[[int(t.split("/")[0]) - 1 for t in tokens]]
                if (q >= low).all() and (q <= high).all() and corners.query(q)[0].max() < 0.03:
                    drop.add(number)
                    count += len(tokens) - 2
        print(name, "triangles to cut:", count, flush=True)
        if count == 0:
            continue
        if count != old_triangles:
            raise SystemExit(f"{name} has {count} of the skip's {old_triangles} triangles: nothing written.")
        kept = [line for number, line in enumerate(lines) if number not in drop]
        final = []
        for number, line in enumerate(kept):
            if line.startswith("usemtl"):
                following = next((x for x in kept[number + 1 :] if x.startswith(("f ", "usemtl"))), "")
                if not following.startswith("f "):
                    continue
            final.append(line)
        out[path] = final

    # The old skip's one collision box, out of the live vmdl.
    path = os.path.join(DIR, VMDLS[s])
    with open(path, encoding="utf-8", newline="") as h:
        lines = h.readlines()
    world = K.to_world((s * OLD_E, N, 23.6))
    wanted = f"origin = [ {world[0]:.4f}, {world[1]:.4f}, 23.6000 ]"
    found = [i for i, line in enumerate(lines) if wanted in line]
    if len(found) > 1:
        raise SystemExit(f"{VMDLS[s]}: {len(found)} boxes at {wanted}: nothing written.")
    if found:
        start = found[0]
        while "{" not in lines[start]:
            start -= 1
        end = found[0]
        while "}" not in lines[end]:
            end += 1
        if "69.4000, 135.8000, 47.2000" not in "".join(lines[start : end + 1]):
            raise SystemExit(f"{VMDLS[s]}: the box at {wanted} isn't the skip's: nothing written.")
        print(VMDLS[s], "collision box out:", wanted, flush=True)
        out[path] = lines[:start] + lines[end + 1 :]

    S.PLACED.clear()
    S.record((s * NEW_E, N, 0.0))
    placed.append(S.PLACED[0])

scene_file = pathlib.Path(M.SCENE_FILE)
scene = json.loads(scene_file.read_text(encoding="utf-8"))
station = next(o for o in scene["GameObjects"] if o.get("Name") == "Station")
names = [o.get("Name") for o in station["Children"]]
group = S.scene_group(placed)
print("scene:", [c["Position"] for c in group["Children"]], "group already there:", "Skips" in names, flush=True)
if not WRITE:
    print("dry run: nothing written", flush=True)
    raise SystemExit(0)
if "Skips" not in names:
    print("new model triangles:", S.write_model(), flush=True)
    station["Children"].insert(names.index("Stacked Tyres") + 1, group)
    K.write_text(scene_file, json.dumps(scene, indent=2), newline=None)
for path, final in out.items():
    temp = path + ".installing"
    with open(temp, "w", encoding="utf-8", newline="") as h:
        h.writelines(final)
        h.flush()
        os.fsync(h.fileno())
    for attempt in range(60):
        try:
            os.replace(temp, path)
            break
        except PermissionError:
            if attempt == 59:
                raise
            print("  waiting for the editor to let go of", os.path.basename(path), flush=True)
            time.sleep(5)
    print("  replaced", os.path.basename(path), flush=True)
print("written", flush=True)
