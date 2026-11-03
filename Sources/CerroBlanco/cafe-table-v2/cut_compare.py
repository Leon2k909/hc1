"""A copy of Cerro Blanco's dressing model without its eight cafe tables, for the in-engine before and after: python cut_compare.py <project root> [--check]

The scene draws quality-v1/cerroblanco_dressing_v2.vmdl, where the tables are merged in. This writes cafe_table_v2/compare/cerroblanco_dressing_cut.obj and its vmdl beside the new model, and
touches nothing the scene uses. OBJ axes are ( -e, z, n ) in plan terms. Each old table was a 20-sided top of radius 14 from 28.5 to 29.5 (white on top, steel round its side and under it), a
six-sided steel bar of radius 1.2 from 1 to 28.5, and in the cafe a 12-sided steel disc of radius 9 under it. The courtyard's discs went with the parasols' install.
"""
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
SRC = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "quality-v1")
DST = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "cafe_table_v2", "compare")
PAINTS = ("cb_white", "cb_steel")
sys.path.insert(0, os.path.join(ROOT, "Sources", "CerroBlanco", "cafe-chair-v2"))
from chairs import COURTYARD, INSIDE  # noqa: E402

SITES = list(INSIDE) + list(COURTYARD)
EXPECTED = {**{k: 122 for k in range(len(INSIDE))}, **{len(INSIDE) + k: 88 for k in range(len(COURTYARD))}}


def which_table(p):
    e, n, z = -p[:, 0], p[:, 2], p[:, 1]
    if z.min() < -0.05 or z.max() > 29.55:
        return None
    for k, (te, tn) in enumerate(SITES):
        if np.hypot(e - te, n - tn).max() <= 14.05:
            return k
    return None


def faces_to_cut(lines, verts):
    current = None
    drop, counts = set(), [0] * len(SITES)
    for i, l in enumerate(lines):
        if l.startswith("usemtl"):
            current = l.split()[1]
        elif l.startswith("f ") and current in PAINTS:
            k = which_table(verts[[int(t.split("/")[0]) - 1 for t in l.split()[1:]]])
            if k is not None:
                drop.add(i)
                counts[k] += 1
    return drop, counts


if __name__ == "__main__":
    lines = open(os.path.join(SRC, "cerroblanco_dressing_v2.obj"), encoding="utf-8").read().split("\n")
    verts = np.array([[float(t) for t in l.split()[1:4]] for l in lines if l.startswith("v ")])
    drop, counts = faces_to_cut(lines, verts)
    print("faces by table", counts, "expected", [EXPECTED[k] for k in range(len(SITES))], flush=True)
    if "--check" in sys.argv:
        raise SystemExit(0)
    os.makedirs(DST, exist_ok=True)
    text = "\n".join(l for i, l in enumerate(lines) if i not in drop).replace("mtllib cerroblanco_dressing_v2.mtl", "mtllib cerroblanco_dressing_cut.mtl")
    open(os.path.join(DST, "cerroblanco_dressing_cut.obj"), "w", encoding="utf-8", newline="\n").write(text)
    open(os.path.join(DST, "cerroblanco_dressing_cut.mtl"), "w", encoding="utf-8", newline="\n").write(open(os.path.join(SRC, "cerroblanco_dressing_v2.mtl"), encoding="utf-8").read())
    vmdl = open(os.path.join(SRC, "cerroblanco_dressing_v2.vmdl"), encoding="utf-8").read()
    old = "models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj"
    assert vmdl.count(old) == 1
    open(os.path.join(DST, "cerroblanco_dressing_cut.vmdl"), "w", encoding="utf-8", newline="\n").write(vmdl.replace(old, "models/maps/cerroblanco/cafe_table_v2/compare/cerroblanco_dressing_cut.obj"))
    print("wrote", DST, flush=True)
