"""A copy of Cerro Blanco's dressing model without the four courtyard parasols, for the in-engine before and after: python cut_compare.py <project root> [--check]

The scene draws quality-v1/cerroblanco_dressing_v2.vmdl, where the parasols are merged in. This writes parasol_v2/compare/cerroblanco_dressing_cut.obj and its vmdl beside the new model, and touches
nothing the scene uses. OBJ axes are ( -e, z, n ) in plan terms. Each parasol was four double-sided triangles from its rib tips at 84 to its peak at 100, a six-sided bar of radius 1.2 from the ground
to 96 (its table's own post is the same bar from 1 to 28.5, which stays), and an 18 x 18 x 3 black box at its foot (with the table's 9 in base disc inside it, which the new base covers).
"""
import os
import sys

import numpy as np

ROOT = sys.argv[1]
SRC = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "quality-v1")
DST = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "parasol_v2", "compare")
SITES = [(-540, 870), (-420, 940), (-540, 990), (-300, 920)]  # Plan ( e, n ) of each courtyard parasol.

lines = open(os.path.join(SRC, "cerroblanco_dressing_v2.obj"), encoding="utf-8").read().split("\n")
verts = np.array([[float(t) for t in l.split()[1:4]] for l in lines if l.startswith("v ")])
print("verts", len(verts), flush=True)


def cut(face_line):
    idx = [int(tok.split("/")[0]) - 1 for tok in face_line.split()[1:]]
    p = verts[idx]
    for e, n in SITES:
        dx, dz, y = p[:, 0] - (-e), p[:, 2] - n, p[:, 1]
        r = np.hypot(dx, dz)
        canopy = (y >= 83.9).all() and (np.abs(dx) <= 44.1).all() and (np.abs(dz) <= 44.1).all()
        pole = (r <= 1.25).all() and y.max() > 50.0
        foot = (np.abs(dx) <= 9.01).all() and (np.abs(dz) <= 9.01).all() and (y <= 3.01).all()
        if canopy:
            return "canopy"
        if pole:
            return "pole"
        if foot:
            return "foot"
    return None


counts = {}
out = []
for l in lines:
    if l.startswith("f "):
        kind = cut(l)
        if kind:
            counts[kind] = counts.get(kind, 0) + 1
            continue
    out.append(l)
print("cut", counts, flush=True)
if "--check" in sys.argv:
    raise SystemExit(0)
os.makedirs(DST, exist_ok=True)
text = "\n".join(out).replace("mtllib cerroblanco_dressing_v2.mtl", "mtllib cerroblanco_dressing_cut.mtl")
open(os.path.join(DST, "cerroblanco_dressing_cut.obj"), "w", encoding="utf-8", newline="\n").write(text)
open(os.path.join(DST, "cerroblanco_dressing_cut.mtl"), "w", encoding="utf-8", newline="\n").write(open(os.path.join(SRC, "cerroblanco_dressing_v2.mtl"), encoding="utf-8").read())
vmdl = open(os.path.join(SRC, "cerroblanco_dressing_v2.vmdl"), encoding="utf-8").read()
old = "models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj"
assert vmdl.count(old) == 1
open(os.path.join(DST, "cerroblanco_dressing_cut.vmdl"), "w", encoding="utf-8", newline="\n").write(vmdl.replace(old, "models/maps/cerroblanco/parasol_v2/compare/cerroblanco_dressing_cut.obj"))
print("wrote", DST, flush=True)
