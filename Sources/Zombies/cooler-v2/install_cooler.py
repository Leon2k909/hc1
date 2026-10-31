"""Swap Riverside's cooler for cooler_v2 without regenerating the map: python install_cooler.py <project root>

As install_drums.py does for the drums, and for the same reason: rerunning Tools/riverside_map.py rewrites far more than one prop. This asks
the map's own code where the cooler is, cuts exactly its faces out of the checked-in riverside_pad.obj, leaves the pad's collision alone, and
adds the same object to the scene that riverside_map.py's write_scene makes. It stops before writing anything if the faces aren't the old
cooler's. Safe to rerun.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import riverside_map as M  # noqa: E402

K, P = M.K, M.P
EXPECTED = {"rs_alu": 56, "rs_cooler": 10, "rs_cooler_white": 24, "rs_drum_inside": 12, "rs_drum_red": 32, "rs_signs": 2}

P.reset()
M.trailers(K.Model(), K.Model(), K.Model())
M.store(K.Model())
M.pad(K.Model())
M.dressing(K.Model())
if len(P.COOLERS) != 1:
    raise SystemExit(f"{len(P.COOLERS)} coolers, not 1. Nothing written.")
position, yaw = P.COOLERS[0]
foot = np.array(K.to_world(position), float)
along = np.array((math.cos(math.radians(yaw)), math.sin(math.radians(yaw))))
side = np.array((-along[1], along[0]))
print("foot", foot.round(2), "yaw %.2f" % yaw, flush=True)

path = os.path.join(ROOT, "Assets", "models", "maps", "riverside", "riverside_pad.obj")
with open(path, encoding="utf-8", newline="") as h:
    lines = h.readlines()
verts = []
for line in lines:
    if line.startswith("v "):
        a, b, c = map(float, line[2:].split()[:3])
        verts.append((c, a, b))
verts = np.array(verts) - foot
local = np.column_stack((verts[:, :2] @ along, verts[:, :2] @ side, verts[:, 2]))

current = None
drop = set()
counts = {}
for n, line in enumerate(lines):
    if line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current in EXPECTED:
        q = local[[int(t.split("/")[0]) - 1 for t in line.split()[1:]]]
        if np.abs(q[:, 0]).max() < 18.0 and np.abs(q[:, 1]).max() < 18.0 and q[:, 2].min() > -0.5 and q[:, 2].max() < 36.0:
            drop.add(n)
            counts[current] = counts.get(current, 0) + len(line.split()) - 3
print("triangles to cut:", counts, flush=True)
if counts and counts != EXPECTED:
    raise SystemExit(f"Those aren't the old cooler's faces (expected {EXPECTED}). Nothing written.")

if drop:
    kept = [line for n, line in enumerate(lines) if n not in drop]
    out = []
    for n, line in enumerate(kept):
        # A usemtl left with no faces goes too.
        if line.startswith("usemtl"):
            following = next((x for x in kept[n + 1 :] if x.startswith(("f ", "usemtl"))), "")
            if not following.startswith("f "):
                continue
        out.append(line)
    with open(path, "w", encoding="utf-8", newline="") as h:
        h.writelines(out)

scene = json.loads(open(M.SCENE_FILE, encoding="utf-8").read())
objects = scene["GameObjects"]
placed = M.cooler_objects()[0]
names = [o.get("Name") for o in objects]
if "Cooler" in names:
    objects[names.index("Cooler")] = placed
else:
    objects.insert(names.index("Burn Drums") + 1, placed)
K.write_text(M.SCENE_FILE, json.dumps(scene, indent=2), newline=None)
print("triangles cut:", sum(counts.values()), "scene: Cooler at", placed["Position"], "rotation", placed["Rotation"], flush=True)
