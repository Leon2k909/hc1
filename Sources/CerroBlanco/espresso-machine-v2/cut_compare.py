"""A copy of Cerro Blanco's fit-out detail model without the cafe's espresso machine, for the in-engine before and after: python cut_compare.py <project root> [--check]

The scene draws cerroblanco_fitout_fine.vmdl ("Fit-out Detail"), where the machine is merged in. This writes espresso_machine_v2/compare/cerroblanco_fitout_fine_cut.obj and its vmdl beside the new
model, and touches nothing the scene uses. OBJ axes are ( -e, z, n ) in plan terms. The old machine (cerroblanco_fitout.cafe) was a steel box 26 x 18 x 17 at plan ( 575, 615 ) on the counter's top
at 42, a cbf_track lid, two chrome stubs with black handles out of its south face, and four open cbf_plastic cones on top.
"""
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = sys.argv[1]
SRC = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco")
DST = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "espresso_machine_v2", "compare")
PAINTS = ("cb_steel", "cbf_track", "cbf_chrome", "cb_black", "cbf_plastic")
SITES = [(575.0, 615.0)]
EXPECTED = None  # Set from the first count: the box, the lid, two groups and handles, four cones.


def which_cup(p):
    e, n, z = -p[:, 0], p[:, 2], p[:, 1]
    if z.min() < 41.9 or z.max() > 64.0:
        return None
    if e.min() >= 561.4 and e.max() <= 588.6 and n.min() >= 598.5 and n.max() <= 625.5:
        return 0
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
    print("faces of the machine", counts, "total", len(drop), flush=True)
    if "--check" in sys.argv:
        raise SystemExit(0)
    os.makedirs(DST, exist_ok=True)
    text = "\n".join(l for i, l in enumerate(lines) if i not in drop).replace("mtllib cerroblanco_fitout_fine.mtl", "mtllib cerroblanco_fitout_fine_cut.mtl")
    open(os.path.join(DST, "cerroblanco_fitout_fine_cut.obj"), "w", encoding="utf-8", newline="\n").write(text)
    open(os.path.join(DST, "cerroblanco_fitout_fine_cut.mtl"), "w", encoding="utf-8", newline="\n").write(open(os.path.join(SRC, "cerroblanco_fitout_fine.mtl"), encoding="utf-8").read())
    vmdl = open(os.path.join(SRC, "cerroblanco_fitout_fine.vmdl"), encoding="utf-8").read()
    old = "models/maps/cerroblanco/cerroblanco_fitout_fine.obj"
    assert vmdl.count(old) == 1
    open(os.path.join(DST, "cerroblanco_fitout_fine_cut.vmdl"), "w", encoding="utf-8", newline="\n").write(vmdl.replace(old, "models/maps/cerroblanco/espresso_machine_v2/compare/cerroblanco_fitout_fine_cut.obj"))
    print("wrote", DST, flush=True)
