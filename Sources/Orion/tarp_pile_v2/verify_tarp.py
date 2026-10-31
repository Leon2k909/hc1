"""Check the tarp pile v2 from its files: python verify_tarp.py <project root> [installed]

Faces outward, normals, UVs, the files it names, and that it wraps the old pile's collision box (x +-32, y +-44, z 0 to 62.4), as nothing else stops a player walking into the cloth. Without "installed" it also checks that Orion doesn't use it yet. Seeing it in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
INSTALLED = "installed" in sys.argv[2:]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/props/orion/tarp_pile_v2")
LIMIT_LOW, LIMIT_HIGH = np.array((-62.0, -76.0, 0.0)), np.array((62.0, 76.0, 66.0))
failures = []
report = {"lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


for lod in range(3):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"tarp_pile_lod{lod}.obj"), encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            v.append(line[2:].split())
        elif tag == "vt":
            vt.append(line[3:].split())
        elif tag == "vn":
            vn.append(line[3:].split())
        elif tag == "f ":
            f.append([tuple(int(i) - 1 for i in tok.split("/")) for tok in line.split()[1:]])
    v, vt, vn, f = np.array(v, float), np.array(vt, float), np.array(vn, float), np.array(f, int)
    tri = v[f[:, :, 0]]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    face_n = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
    agree = float(((vn[f[:, :, 2]].mean(1) * face_n).sum(1) > 0).mean())
    e = v[:, [2, 0, 1]]
    lo, hi = e.min(0), e.max(0)
    check(agree > 0.97, f"lod{lod}: only {agree:.3f} of faces agree with their normals")
    check(np.isfinite(v).all() and np.isfinite(vt).all(), f"lod{lod}: non-finite values")
    check(((vt >= -1e-4) & (vt <= 1 + 1e-4)).all(), f"lod{lod}: UVs outside the atlas")
    check((lo >= LIMIT_LOW - 0.1).all() and (hi <= LIMIT_HIGH + 0.1).all(), f"lod{lod}: bounds {lo.round(2)} {hi.round(2)} past the limit")
    check(lo[2] < 1.0 and hi[2] > 60.0, f"lod{lod}: doesn't cover the old collision box's height: {lo.round(2)} {hi.round(2)}")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), bounds=[lo.round(2).tolist(), hi.round(2).tolist()])

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "tarp_pile_lod0.obj"), "tp_tarp"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, "solid parts are inside out: " + outward.stdout)

doc = open(os.path.join(NEW, "tarp_pile.vmdl"), encoding="utf-8").read()
for ref in re.findall(r'filename = "([^"]+)"', doc) + re.findall(r'to = "([^"]+)"', doc):
    check(os.path.exists(os.path.join(ASSETS, ref)), f"the vmdl names {ref}, which isn't there")
check("PhysicsShapeList" not in doc, "Orion's own collider stands in: the model shouldn't have physics")
vmat = open(os.path.join(ASSETS, "materials/orion/tarp_pile_v2/tp_tarp.vmat"), encoding="utf-8").read()
for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")

tool = open(os.path.join(ROOT, "Tools/orion_map.py"), encoding="utf-8").read()
scene = open(os.path.join(ASSETS, "scenes/maps/Orion/orion.scene"), encoding="utf-8").read()
if INSTALLED:
    check("tarp_pile_v2" in tool and "tarp_pile_v2" in scene, "Orion doesn't use it")
else:
    check("tarp_pile_v2" not in tool and "tarp_pile_v2" not in scene, "Orion already uses it")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
