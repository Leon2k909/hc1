"""Which faces of the built mast point into solid? blender -b --factory-startup --python check_faces.py -- <work dir> [object]

check_outward.py works on closed pieces only (it reads the sign of a piece's volume), and the mast's tubes and rings are open
at the ends, so this is the per-face check: a ray from just outside each face along its normal has to leave the model without
crossing a surface an odd number of times. Prints the parts with faces that fail, with how many and where.
"""
import json
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK = argv[0]
NAME = argv[1] if len(argv) > 1 else "mast_lod0"
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "mast_build.blend"))
parts = json.load(open(os.path.join(WORK, "mast.json")))["parts"]
ob = bpy.data.objects[NAME]
bm = bmesh.new()
bm.from_mesh(ob.data)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bm.faces.ensure_lookup_table()
facts = bm.loops.layers.float_color["facts"]
tree = BVHTree.FromBMesh(bm)
bad = {}
total = {}
slots = [m.name if m else "" for m in ob.data.materials]
for f in bm.faces:
    key = str(round(f.loops[0][facts][1], 4))
    info = parts.get(key, {"name": "?" + key})
    label = info["name"] + (" (" + slots[f.material_index] + ")" if f.material_index < len(slots) else "")
    total[label] = total.get(label, 0) + 1
    n = f.normal
    origin = f.calc_center_median() + n * 0.003
    hits = 0
    cur = origin
    for _ in range(12):
        loc, nor, idx, dist = tree.ray_cast(cur, n, 600.0)
        if loc is None:
            break
        hits += 1
        cur = loc + n * 0.003
    if hits % 2 == 1:
        bad.setdefault(label, []).append((f.calc_center_median().x, f.calc_center_median().y, f.calc_center_median().z))
print("faces", len(bm.faces), "failing", sum(len(v) for v in bad.values()), flush=True)
for label, pts in sorted(bad.items(), key=lambda kv: -len(kv[1])):
    a = np.array(pts)
    print("  %-28s %4d of %4d  centre %s" % (label, len(pts), total[label], np.round(a.mean(0), 1)), flush=True)
print("faces checked", flush=True)
