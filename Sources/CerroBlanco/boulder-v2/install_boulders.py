"""Swap four of Cerro Blanco's six garden boulders for boulder_v2 without regenerating the map: python install_boulders.py <project root> [--write]

The other two stay as they are, since the user wanted the old shape and both new ones in use. This asks the map's own code what each old stone was, cuts only its faces from
what's drawn (quality-v1/cerroblanco_dressing_v2.obj) and from the generator's OBJ, cuts its collision hull, and adds a "Garden Boulders" group to the scene, which is
what cerroblanco_boulders.scene_group() makes on a full run. It stops before writing anything if a stone isn't found as expected. Without --write it only reports.
"""
import json
import math
import os
import pathlib
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import cerroblanco_boulders as B  # noqa: E402
import cerroblanco_map as M  # noqa: E402
import cerroblanco_parts as P  # noqa: E402
import map_kit as K  # noqa: E402

DIR = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco")
DRAWN = ("quality-v1/cerroblanco_dressing_v2.obj", "cerroblanco_dressing.obj")
HULLS = "cerroblanco_dressing_hulls_default.obj"
GARDEN = M.GARDEN
LIST = ((45, 320, (34, 26, 28)), (140, 300, (30, 30, 34)), (228, 340, (38, 28, 30)), (312, 290, (26, 24, 26)), (70, 400, (22, 20, 20)), (200, 410, (24, 22, 22)))

stones = {}
for k, (a, r, size) in enumerate(LIST):
    position = (GARDEN[0] + r * math.cos(math.radians(a)), GARDEN[1] + r * math.sin(math.radians(a)), 1.0)
    model = K.Model()
    P.boulder(model, position, size, 700 + k)
    points = np.array([K.to_world(p) for p in model.hulls[0][0]])
    stones[k] = dict(position=position, points=points, centre=K.to_world(position), polygons=len(model.polygons[P.ROCK]))


def read(path):
    with open(path, encoding="utf-8", newline="") as h:
        lines = h.readlines()
    v = np.array([line[2:].split()[:3] for line in lines if line.startswith("v ")], float)[:, [2, 0, 1]]
    return lines, v


def which_stone(corners):
    for k, stone in stones.items():
        if np.hypot(corners[:, 0] - stone["centre"][0], corners[:, 1] - stone["centre"][1]).max() < 50.0:
            return k
    return None


out = {}
for name in DRAWN:
    path = os.path.join(DIR, name)
    lines, v = read(path)
    current = None
    drop = set()
    counts = {k: 0 for k in stones}
    strays = 0
    for n, line in enumerate(lines):
        if line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current == P.ROCK:
            corners = v[[int(t.split("/")[0]) - 1 for t in line.split()[1:]]]
            k = which_stone(corners)
            if k is None:
                strays += 1
                continue
            counts[k] += 1
            if k in B.NEW:
                drop.add(n)
    print(name, "rock faces per stone", counts, "elsewhere", strays, flush=True)
    if any(counts[k] == 0 for k in stones):
        raise SystemExit(f"Not every stone was found in {name}: nothing written.")
    out[path] = [line for n, line in enumerate(lines) if n not in drop]

# The hulls: each connected element of the hull file is one hull, and an old stone's has only corners of that stone.
path = os.path.join(DIR, HULLS)
lines, v = read(path)
parent = list(range(len(v)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


faces = []
for n, line in enumerate(lines):
    if line.startswith("f "):
        indices = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
        faces.append((n, indices))
        for i in indices[1:]:
            parent[find(i)] = find(indices[0])
elements = {}
for n, indices in faces:
    elements.setdefault(find(indices[0]), []).append((n, indices))
drop = set()
found = {}
for root, members in elements.items():
    corners = v[sorted({i for _, indices in members for i in indices})]
    for k, stone in stones.items():
        gap = np.linalg.norm(corners[:, None, :] - stone["points"][None, :, :], axis=2).min(1).max()
        if gap < 0.02:
            found[k] = found.get(k, 0) + 1
            if k in B.NEW:
                drop.update(n for n, _ in members)
print("hull elements in", HULLS, ":", len(elements), "; found per stone", found, flush=True)
if sorted(found) != sorted(stones) or any(c != 1 for c in found.values()):
    raise SystemExit("Each stone should have exactly one hull: nothing written.")
out[path] = [line for n, line in enumerate(lines) if n not in drop]

scene_file = pathlib.Path(M.SCENE_FILE)
scene = json.loads(scene_file.read_text(encoding="utf-8"))
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Cerro Blanco")
names = [o.get("Name") for o in world["Children"]]
group = B.scene_group(M.ids, {k: stones[k]["position"] for k in B.NEW})
print("scene:", len(group["Children"]), "boulders, group already there:", "Garden Boulders" in names, flush=True)
for child in group["Children"]:
    print("  ", child["Name"], child["Position"], child["Rotation"], child["Scale"], flush=True)
if not WRITE:
    print("dry run: nothing written", flush=True)
    raise SystemExit(0)
if "Garden Boulders" in names:
    world["Children"][names.index("Garden Boulders")] = group
else:
    world["Children"].insert(names.index("Dressing") + 1, group)
K.write_text(scene_file, json.dumps(scene, indent=2), newline=None)
for path, final in out.items():
    temp = path + ".installing"
    with open(temp, "w", encoding="utf-8", newline="") as h:
        h.writelines(final)
        h.flush()
        os.fsync(h.fileno())
    os.replace(temp, path)
print("written", flush=True)
