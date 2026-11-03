"""A copy of Cerro Blanco's fit-out detail model without its 16 cafe cups, for the in-engine before and after: python cut_compare.py <project root> [--check]

The scene draws cerroblanco_fitout_fine.vmdl ("Fit-out Detail"), where the cups are merged in. This writes cafe_cup_v2/compare/cerroblanco_fitout_fine_cut.obj and its vmdl beside the new model, and
touches nothing the scene uses. OBJ axes are ( -e, z, n ) in plan terms. Each old cup was a 12-sided cbf_plastic saucer of radius 2.6 from 29.5 to 29.8 and a ten-sided open cone on it to 32.4.
"""
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cups import cups  # noqa: E402

ROOT = sys.argv[1]
SRC = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco")
DST = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "cafe_cup_v2", "compare")
PAINTS = ("cbf_plastic",)
SITES = cups()


def which_cup(p):
    e, n, z = -p[:, 0], p[:, 2], p[:, 1]
    if z.min() < 29.45 or z.max() > 32.5:
        return None
    for k, (ce, cn, _) in enumerate(SITES):
        if np.hypot(e - ce, n - cn).max() <= 2.65:
            return k
    return None


def faces_to_cut(lines, verts):
    current = None
    drop, counts = set(), [0] * len(SITES)
    for i, l in enumerate(lines):
        if l.startswith("usemtl"):
            current = l.split()[1]
        elif l.startswith("f ") and current in PAINTS:
            k = which_cup(verts[[int(t.split("/")[0]) - 1 for t in l.split()[1:]]])
            if k is not None:
                drop.add(i)
                counts[k] += 1
    return drop, counts


if __name__ == "__main__":
    lines = open(os.path.join(SRC, "cerroblanco_fitout_fine.obj"), encoding="utf-8").read().split("\n")
    verts = np.array([[float(t) for t in l.split()[1:4]] for l in lines if l.startswith("v ")])
    drop, counts = faces_to_cut(lines, verts)
    print("faces by cup", counts, "total", len(drop), flush=True)
    if "--check" in sys.argv:
        raise SystemExit(0)
    os.makedirs(DST, exist_ok=True)
    text = "\n".join(l for i, l in enumerate(lines) if i not in drop).replace("mtllib cerroblanco_fitout_fine.mtl", "mtllib cerroblanco_fitout_fine_cut.mtl")
    open(os.path.join(DST, "cerroblanco_fitout_fine_cut.obj"), "w", encoding="utf-8", newline="\n").write(text)
    open(os.path.join(DST, "cerroblanco_fitout_fine_cut.mtl"), "w", encoding="utf-8", newline="\n").write(open(os.path.join(SRC, "cerroblanco_fitout_fine.mtl"), encoding="utf-8").read())
    vmdl = open(os.path.join(SRC, "cerroblanco_fitout_fine.vmdl"), encoding="utf-8").read()
    old = "models/maps/cerroblanco/cerroblanco_fitout_fine.obj"
    assert vmdl.count(old) == 1
    open(os.path.join(DST, "cerroblanco_fitout_fine_cut.vmdl"), "w", encoding="utf-8", newline="\n").write(vmdl.replace(old, "models/maps/cerroblanco/cafe_cup_v2/compare/cerroblanco_fitout_fine_cut.obj"))
    print("wrote", DST, flush=True)
