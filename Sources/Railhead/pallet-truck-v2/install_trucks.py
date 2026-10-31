"""Swap Railhead's two pallet trucks for pallet_truck_v2 without regenerating the map: python install_trucks.py <project root> [--write]

The old trucks are merged into the dress models, and railhead_dress_east and _west build from extinguisher-v2/east-base.obj and west-base.obj, so the cut goes there as well as in the generator's OBJs. Every corner of a cut
face must be one of the old truck's, and each truck must lose exactly the old model's triangles, or nothing is written. Their collision stays, in the vmdls. Then it adds a "Pallet Trucks" group to the scene, which is what
railhead_pallet_trucks.scene_group() makes on a full run. Without --write it only reports. An open editor recompiles the models by itself.
"""
import json
import os
import pathlib
import sys
import tempfile

import numpy as np
from scipy.spatial import cKDTree

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import railhead_furniture as FU  # noqa: E402
import railhead_map as M  # noqa: E402
import railhead_pallet_trucks as T  # noqa: E402

DIR = os.path.join(ROOT, "Assets", "models", "maps", "railhead")
FILES = {-1.0: ("extinguisher-v2/west-base.obj", "railhead_dress_west.obj"), 1.0: ("extinguisher-v2/east-base.obj", "railhead_dress_east.obj")}
PAINTS = {"rw_red_paint", "rw_rubber", "rw_black"}

model = K.Model()
FU.pallet_jack(model, 0.0, 0.0, "n")
for paint in model.polygons:
    model.tile_overrides[paint] = 64.0
with tempfile.TemporaryDirectory() as scratch:
    target = pathlib.Path(scratch) / "old_truck.obj"
    K.write_obj(target, model, "old_truck")
    text = open(target, encoding="utf-8").read().splitlines()
old = np.array([line[2:].split()[:3] for line in text if line.startswith("v ")], float)[:, [2, 0, 1]]
old_triangles = sum(len(line.split()) - 3 for line in text if line.startswith("f "))
corners = cKDTree(old)
print("old truck:", old_triangles, "triangles, x", old[:, 0].min(), old[:, 0].max(), "y", old[:, 1].min(), old[:, 1].max(), "z", old[:, 2].max(), flush=True)

# Which side's file holds which truck isn't taken on trust: the counts say.
placed = []
out = {}
for s, names in FILES.items():
    e, n = s * 1935.0, -2290.0
    at = K.to_world((e, n, 0.0))
    placed.append((at.round(3), 0.0))
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
                q = v[[int(t.split("/")[0]) - 1 for t in tokens]] - at
                if np.abs(q[:, 0]).max() < 60 and np.abs(q[:, 1]).max() < 15 and corners.query(q)[0].max() < 0.03:
                    drop.add(number)
                    count += len(tokens) - 2
        print(name, "truck at", at.round(1).tolist(), "triangles to cut:", count, flush=True)
        if count != old_triangles:
            raise SystemExit(f"{name} has {count} of the truck's {old_triangles} triangles: nothing written.")
        kept = [line for number, line in enumerate(lines) if number not in drop]
        final = []
        for number, line in enumerate(kept):
            if line.startswith("usemtl"):
                following = next((x for x in kept[number + 1 :] if x.startswith(("f ", "usemtl"))), "")
                if not following.startswith("f "):
                    continue
            final.append(line)
        out[path] = final

scene_file = pathlib.Path(M.SCENE_FILE)
scene = json.loads(scene_file.read_text(encoding="utf-8"))
station = next(o for o in scene["GameObjects"] if o.get("Name") == "Station")
names = [o.get("Name") for o in station["Children"]]
group = T.scene_group(placed)
print("scene:", len(group["Children"]), "trucks, group already there:", "Pallet Trucks" in names, [c["Position"] for c in group["Children"]], flush=True)
if not WRITE:
    print("dry run: nothing written", flush=True)
    raise SystemExit(0)
if "Pallet Trucks" in names:
    station["Children"][names.index("Pallet Trucks")] = group
else:
    station["Children"].insert(names.index("Station Bins") + 1, group)
K.write_text(scene_file, json.dumps(scene, indent=2), newline=None)
for path, final in out.items():
    temp = path + ".installing"
    with open(temp, "w", encoding="utf-8", newline="") as h:
        h.writelines(final)
        h.flush()
        os.fsync(h.fileno())
    os.replace(temp, path)
print("written", flush=True)
