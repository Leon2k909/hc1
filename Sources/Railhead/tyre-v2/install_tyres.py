"""Swap Railhead's stacked tyres for tyre_v2 without regenerating the map: python install_tyres.py <project root> [--write]

The old tyres are merged into the dress models, and railhead_dress_east and _west build from extinguisher-v2/east-base.obj and west-base.obj, so the cut goes there as well as in the generator's OBJs. This builds each old stack with the map's own numbers.
Every corner of a cut face must be one of those stacks', and each file must lose exactly their triangles, or nothing is written. The stacks' collision stays, in the vmdls. Then it adds a "Stacked Tyres" group to the scene, which is what
railhead_tyres.scene_group() makes on a full run. Without --write it only reports. An open editor recompiles the models by itself.
"""
import json
import math
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
import railhead_dress_detail as D  # noqa: E402
import railhead_map as M  # noqa: E402
import railhead_tyres as T  # noqa: E402

DIR = os.path.join(ROOT, "Assets", "models", "maps", "railhead")
FILES = {-1.0: ("extinguisher-v2/west-base.obj", "railhead_dress_west.obj"), 1.0: ("extinguisher-v2/east-base.obj", "railhead_dress_east.obj")}
PAINTS = {"dress_tyre", "rw_black"}
# As railhead_map.yard_clutter: off the bank's face, n, count, lean.
STACKS = ((16.0, -2160.0, 4, 0.0), (17.0, -2128.0, 2, 0.0), (18.0, -2060.0, 3, 0.4))
HEIGHT = 8.07
Z0 = 0.3

placed = []
out = {}
for s, names in FILES.items():
    model = K.Model()
    for off, n, count, lean in STACKS:
        e = s * M.BANK_FACE + s * off
        D.tyre_stack_old(model, e, n, Z0, count, lean)
        for k in range(count):
            de = math.sin(k * 2.1) * 1.4 + lean * k
            dn = math.cos(k * 1.7) * 1.2
            T.PLACED.clear()
            T.record((e + de, n + dn, Z0 + k * HEIGHT), T.index_for(e, n, k))
            placed.append(T.PLACED[0])
    for paint in model.polygons:
        model.tile_overrides[paint] = 64.0
    with tempfile.TemporaryDirectory() as scratch:
        target = pathlib.Path(scratch) / "old_tyres.obj"
        K.write_obj(target, model, "old_tyres")
        text = open(target, encoding="utf-8").read().splitlines()
    old = np.array([line[2:].split()[:3] for line in text if line.startswith("v ")], float)[:, [2, 0, 1]]
    old_triangles = sum(len(line.split()) - 3 for line in text if line.startswith("f "))
    corners = cKDTree(old)
    low, high = old.min(0) - 1, old.max(0) + 1
    print("side", s, "old stacks:", old_triangles, "triangles, paints", sorted(model.polygons), flush=True)
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
        if count != old_triangles:
            raise SystemExit(f"{name} has {count} of the stacks' {old_triangles} triangles: nothing written.")
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
print("scene:", len(group["Children"]), "tyres, group already there:", "Stacked Tyres" in names, [c["Position"] for c in group["Children"]][:4], flush=True)
if not WRITE:
    print("dry run: nothing written", flush=True)
    raise SystemExit(0)
if "Stacked Tyres" in names:
    station["Children"][names.index("Stacked Tyres")] = group
else:
    station["Children"].insert(names.index("Pallet Trucks") + 1, group)
K.write_text(scene_file, json.dumps(scene, indent=2), newline=None)
for path, final in out.items():
    temp = path + ".installing"
    with open(temp, "w", encoding="utf-8", newline="") as h:
        h.writelines(final)
        h.flush()
        os.fsync(h.fileno())
    os.replace(temp, path)
print("written", flush=True)
