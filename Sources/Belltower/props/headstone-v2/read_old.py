"""Measure the churchyard's old headstones from the model the game draws: python read_old.py <project root> <out json>

Each is one box, or two for a cross, in Belltower's merged west half, on the ashlar_grey material. Writes each stone's place, turn and kind in the
map's west half (engine axes), which the render and the install both go by. The east half is its mirror.
"""
import json
import math
import os
import sys

import numpy as np

ROOT, OUT = sys.argv[1], sys.argv[2]
path = os.path.join(ROOT, "Assets/models/maps/belltower/compiler-safe/west/west_001_ashlar_grey.obj")
v, f = [], []
for line in open(path, encoding="utf-8"):
    if line.startswith("v "):
        a, b, c = map(float, line[2:].split())
        v.append((c, a, b))  # OBJ (a, b, c) is engine (c, a, b).
    elif line.startswith("f "):
        f.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
v = np.array(v)
# From the map script: plan e -610 to -250, n -470 to -870, so engine X = n, Y = -e. A generous margin: the arms alone reach 12 in, and they're shifted at random.
faces = [x for x in f if all(-900 < v[i, 0] < -440 and 220 < v[i, 1] < 640 and -0.01 < v[i, 2] < 41 for i in x)]
parent = {}


def find(i):
    parent.setdefault(i, i)
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


# A box's faces may not share vertices, so corners in the same place count as one.
ids = {}
for face in faces:
    keys = [ids.setdefault(tuple(np.round(v[i], 2)), i) for i in face]
    for k in keys[1:]:
        parent[find(k)] = find(keys[0])
groups = {}
for key, i in ids.items():
    groups.setdefault(find(i), []).append(key)
slabs, shafts, arms = [], [], []
for corners in groups.values():
    if len(corners) != 8:
        continue
    c = np.array(corners)
    centre = c[:, :2].mean(0)
    reach = float(np.linalg.norm(c[:, :2] - centre, axis=1).max())
    z0, z1 = float(c[:, 2].min()), float(c[:, 2].max())
    across = np.linalg.svd(c[:, :2] - centre)[2][0]
    item = dict(centre=centre.tolist(), across=across.tolist(), z1=z1)
    if z0 < 0.1 and abs(reach - math.hypot(11, 3)) < 0.1:
        slabs.append(item)
    elif z0 < 0.1 and abs(z1 - 40) < 0.1 and abs(reach - math.hypot(3, 3)) < 0.1:
        shafts.append(item)
    elif abs(z0 - 26) < 0.1 and abs(z1 - 32) < 0.1 and abs(reach - math.hypot(12, 3)) < 0.1:
        arms.append(item)
stones = []


def place(kind, item, across, height):
    # Every stone in the script shares one facing, give or take five degrees: local +X (the inscribed face) towards engine +X.
    yaw = math.degrees(math.atan2(across[1], across[0])) - 90.0
    yaw = (yaw + 90.0) % 180.0 - 90.0
    stones.append(dict(kind=kind, x=item["centre"][0], y=item["centre"][1], yaw=yaw, height=height))


for s in slabs:
    place("slab", s, s["across"], s["z1"])
for s in shafts:
    arm = min(arms, key=lambda a: math.dist(a["centre"], s["centre"]))
    if math.dist(arm["centre"], s["centre"]) > 0.5:
        sys.exit(f"a cross's shaft has no arms: {s}")
    place("cross", s, arm["across"], s["z1"])
stones.sort(key=lambda s: (s["x"], s["y"]))
print(len(stones), "stones:", len(shafts), "crosses,", len(slabs), "slabs,", len(arms), "arms")
print("heights", sorted(round(s["height"], 1) for s in stones if s["kind"] == "slab"))
print("yaws", sorted(round(s["yaw"], 1) for s in stones))
json.dump(stones, open(OUT, "w"), indent=1)
