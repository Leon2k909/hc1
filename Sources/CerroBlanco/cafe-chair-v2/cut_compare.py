"""A copy of Cerro Blanco's dressing model without its 20 cafe chairs, for the in-engine before and after: python cut_compare.py <project root> [--check]

The scene draws quality-v1/cerroblanco_dressing_v2.vmdl, where the chairs are merged in. This writes cafe_chair_v2/compare/cerroblanco_dressing_cut.obj and its vmdl beside the new model, and
touches nothing the scene uses. OBJ axes are ( -e, z, n ) in plan terms. Each old chair was a 16 x 16 teak slab at 17.5, four square steel bars under it, two more leaning back to 33 and a teak board
across them: cb_teak and cb_steel faces inside the chair's own box, from 9.8 behind its middle to 8.2 in front and 8.2 to each side.
"""
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chairs import chairs  # noqa: E402

ROOT = sys.argv[1]
SRC = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "quality-v1")
DST = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "cafe_chair_v2", "compare")
PAINTS = ("cb_teak", "cb_steel")
SITES = chairs()


def which_chair(p):
    """The chair a face belongs to, from its corners in OBJ axes, or None."""
    e, n, z = -p[:, 0], p[:, 2], p[:, 1]
    if z.min() < -0.1 or z.max() > 33.3:
        return None
    for k, (ce, cn, yaw) in enumerate(SITES):
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        x = (e - ce) * c + (n - cn) * s
        y = -(e - ce) * s + (n - cn) * c
        if x.min() >= -9.8 and x.max() <= 8.2 and np.abs(y).max() <= 8.2:
            return k
    return None


def faces_to_cut(lines, verts):
    current = None
    drop, counts = set(), [0] * len(SITES)
    for i, l in enumerate(lines):
        if l.startswith("usemtl"):
            current = l.split()[1]
        elif l.startswith("f ") and current in PAINTS:
            k = which_chair(verts[[int(t.split("/")[0]) - 1 for t in l.split()[1:]]])
            if k is not None:
                drop.add(i)
                counts[k] += 1
    return drop, counts


if __name__ == "__main__":
    lines = open(os.path.join(SRC, "cerroblanco_dressing_v2.obj"), encoding="utf-8").read().split("\n")
    verts = np.array([[float(t) for t in l.split()[1:4]] for l in lines if l.startswith("v ")])
    drop, counts = faces_to_cut(lines, verts)
    print("faces by chair", counts, "total", len(drop), flush=True)
    if "--check" in sys.argv:
        raise SystemExit(0)
    os.makedirs(DST, exist_ok=True)
    text = "\n".join(l for i, l in enumerate(lines) if i not in drop).replace("mtllib cerroblanco_dressing_v2.mtl", "mtllib cerroblanco_dressing_cut.mtl")
    open(os.path.join(DST, "cerroblanco_dressing_cut.obj"), "w", encoding="utf-8", newline="\n").write(text)
    open(os.path.join(DST, "cerroblanco_dressing_cut.mtl"), "w", encoding="utf-8", newline="\n").write(open(os.path.join(SRC, "cerroblanco_dressing_v2.mtl"), encoding="utf-8").read())
    vmdl = open(os.path.join(SRC, "cerroblanco_dressing_v2.vmdl"), encoding="utf-8").read()
    old = "models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj"
    assert vmdl.count(old) == 1
    open(os.path.join(DST, "cerroblanco_dressing_cut.vmdl"), "w", encoding="utf-8", newline="\n").write(vmdl.replace(old, "models/maps/cerroblanco/cafe_chair_v2/compare/cerroblanco_dressing_cut.obj"))
    print("wrote", DST, flush=True)
