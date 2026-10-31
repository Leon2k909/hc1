"""Finish the bins' install in the east and west models: python install_bins_published.py <project root> [--write]

install_bins.py cut the OBJs the generator writes, but railhead_dress_east and _west don't build from those. Since the extinguisher swap (docs/notes/089) their vmdls
name extinguisher-v2/east-base.obj and west-base.obj, so cutting the others changed nothing in the game. This makes the same cut in those two, at the places in
placements.json, with the same check: every corner must be one of the old bin's, and each bin must lose exactly its 280 triangles, or nothing is written.
Without --write it only reports. An open editor recompiles the two models by itself, which stalls it for minutes, so ask first if other sessions are using it.
"""
import collections
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
import railhead_furniture as FU  # noqa: E402
import railhead_props as P  # noqa: E402

DIR = os.path.join(ROOT, "Assets", "models", "maps", "railhead", "extinguisher-v2")
PLACEMENTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "placements.json")
FILES = ("east-base.obj", "west-base.obj")
PAINTS = {"rw_steel_dark", "rw_stainless", "rw_black", "rw_rubber", "rw_prop_signs"}
OLD_TRIANGLES = 280
FRONT, BACK, HALF, TALL = 9.65, -8.75, 20.15, 39.67

bins = [(np.array(at), yaw) for at, yaw in json.load(open(PLACEMENTS))]
frames = [(at, np.array((math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))), np.array((-math.sin(math.radians(yaw)), math.cos(math.radians(yaw))))) for at, yaw in bins]
grid = collections.defaultdict(list)
for k, (at, _, _) in enumerate(frames):
    for gx in range(int(at[0] // 64) - 1, int(at[0] // 64) + 2):
        for gy in range(int(at[1] // 64) - 1, int(at[1] // 64) + 2):
            grid[(gx, gy)].append(k)

model = K.Model()
FU.bin(model, P.frame_for(0.0, 0.0, 0.0, "+n"))
for paint in model.polygons:
    model.tile_overrides[paint] = 64.0
with tempfile.TemporaryDirectory() as scratch:
    target = pathlib.Path(scratch) / "old_bin.obj"
    K.write_obj(target, model, "old_bin")
    old_corners = cKDTree(np.array([line[2:].split()[:3] for line in open(target, encoding="utf-8") if line.startswith("v ")], float)[:, [2, 0, 1]])

counts = [0] * len(frames)
out = {}
for name in FILES:
    path = os.path.join(DIR, name)
    with open(path, encoding="utf-8", newline="") as h:
        lines = h.readlines()
    v = np.array([line[2:].split()[:3] for line in lines if line.startswith("v ")], float)[:, [2, 0, 1]]
    current = None
    drop = set()
    for n, line in enumerate(lines):
        if line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current in PAINTS:
            tokens = line.split()[1:]
            q = v[[int(t.split("/")[0]) - 1 for t in tokens]]
            for k in grid.get((int(q[0, 0] // 64), int(q[0, 1] // 64)), ()):
                at, forward, left = frames[k]
                d = q - at
                x, y, z = d[:, :2] @ forward, d[:, :2] @ left, d[:, 2]
                if x.min() > BACK and x.max() < FRONT and np.abs(y).max() < HALF and z.min() > -0.05 and z.max() < TALL:
                    if old_corners.query(np.column_stack((x, y, z)))[0].max() < 0.03:
                        drop.add(n)
                        counts[k] += len(tokens) - 2
                        break
    # A usemtl left with no faces goes too.
    kept = [line for n, line in enumerate(lines) if n not in drop]
    final = []
    for n, line in enumerate(kept):
        if line.startswith("usemtl"):
            following = next((x for x in kept[n + 1 :] if x.startswith(("f ", "usemtl"))), "")
            if not following.startswith("f "):
                continue
        final.append(line)
    out[path] = (final, len(drop))
    print(name, "faces to cut:", len(drop), flush=True)

print("triangles per bin:", collections.Counter(counts), flush=True)
# The centre's three are in railhead_dress_centre.obj, already cut, so they find nothing here.
wrong = [(bins[k][0].tolist(), c) for k, c in enumerate(counts) if c not in (0, OLD_TRIANGLES)]
if wrong or sum(1 for c in counts if c == OLD_TRIANGLES) != 26:
    raise SystemExit(f"Expected 26 bins of {OLD_TRIANGLES} triangles, got {collections.Counter(counts)}, odd ones {wrong}. Nothing written.")
if not WRITE:
    print("dry run: nothing written", flush=True)
    raise SystemExit(0)
for path, (final, dropped) in out.items():
    temp = path + ".installing"
    with open(temp, "w", encoding="utf-8", newline="") as h:
        h.writelines(final)
        h.flush()
        os.fsync(h.fileno())
    os.replace(temp, path)
    print("wrote", os.path.basename(path), "cut", dropped, flush=True)
