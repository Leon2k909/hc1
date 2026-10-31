"""Check the pew from its files: python verify_pew.py <project root> <export dir>

Its parts must face outward, its bounds must fit the old pew's, its collision must be the old two boxes, its textures must exist,
and the old pews must be as committed. Compiling and seeing it in s&box is not covered.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, EXPORT = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(EXPORT, "models/props/belltower/pew_v2")
MATS = "materials/belltower/pew_v2"
OLD_OBJ = "models/maps/belltower/belltower_centre.obj"
NAME = "pew"
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def read_obj(path):
    v, f = [], 0
    for line in open(path, encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    return np.array(v, float)[:, [2, 0, 1]], f  # OBJ (a, b, c) is engine (c, a, b).


def old_pews(lines):
    """The twelve old pews' faces, as text. OBJ (a, b, c) is engine (c, a, b): X is c, Y is a, Z is b."""
    v, current, out = [], None, []
    rows = (-440, -484, -528, -572, -700, -744)
    for line in lines:
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current in ("planks", "planks_dark"):
            corners = [v[int(t.split("/")[0]) - 1] for t in line.split()[1:]]
            xs = [float(c[2]) for c in corners]
            ys = [abs(float(c[0])) for c in corners]
            zs = [float(c[1]) for c in corners]
            if max(zs) <= 38.01 and min(ys) >= 39.9 and max(ys) <= 140.1 and any(min(xs) >= r - 18.01 and max(xs) <= r + 0.01 for r in rows):
                out.append(tuple(tuple(c) for c in corners))
    return out


# From the map script: seat x +-9, back up to 38, y +-50.
want_lo, want_hi = np.array((-9.0, -50.0, 0.0)), np.array((9.0, 50.0, 38.0))
for lod in range(4):
    v, f = read_obj(os.path.join(NEW, f"{NAME}_lod{lod}.obj"))
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    if lod == 0:
        # The hymn racks hang 2.5 in behind the old box, and the seat pads 1.6 in above the seat, not above the back.
        check(lo[0] >= -12.5 and hi[0] <= 9.5 and abs(lo[1] + 50) < 0.5 and abs(hi[1] - 50) < 0.5 and abs(lo[2]) < 0.1 and abs(hi[2] - 38) < 0.5, f"lod0 doesn't fit the old pew: {lo} {hi}")
    if lod:
        check(f < report[f"lod{lod - 1}"]["triangles"], f"lod{lod} isn't lighter")
outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{NAME}_lod0.obj"), NAME], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, report["outward"])
vmdl = open(os.path.join(NEW, f"{NAME}.vmdl"), encoding="utf-8").read()
check("dimensions = [ 18.0000, 100.0000, 18.0000 ]" in vmdl and "origin = [ 0.0000, 0.0000, 9.0000 ]" in vmdl, "seat box isn't the old one")
check("dimensions = [ 3.0000, 100.0000, 20.0000 ]" in vmdl and "origin = [ -7.5000, 0.0000, 28.0000 ]" in vmdl, "back box isn't the old one")
for ref in re.findall(r'filename = "([^"]+)"', vmdl):
    check(os.path.exists(os.path.join(EXPORT, ref)), f"vmdl names missing {ref}")
check(f'to = "{MATS}/{NAME}.vmat"' in vmdl, "vmdl doesn't remap to its material")
vmat = open(os.path.join(EXPORT, MATS, f"{NAME}.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
report["textures"] = textures
check(len(textures) == 5, "expected five textures")
for tex in textures:
    check(os.path.exists(os.path.join(EXPORT, tex)), f"missing {tex}")
now = old_pews(open(os.path.join(ASSETS, OLD_OBJ), encoding="utf-8"))
# The merged model is in git LFS, so `git show` would return a pointer: git status says whether it has changed.
changed = subprocess.run(["git", "status", "--porcelain", "--", f"Assets/{OLD_OBJ}"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
report["old_pew_faces"] = len(now)
check(len(now) == 288, f"expected the twelve old pews' 288 faces, found {len(now)}")
check(changed == "", f"the old merged model changed: {changed}")
report["in_assets"] = [p for p in ("models/props/belltower/pew_v2", MATS) if os.path.exists(os.path.join(ASSETS, p))]
report["compiled_files"] = [f for d in (NEW, os.path.join(EXPORT, MATS)) for f in os.listdir(d) if f.endswith("_c")]
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
