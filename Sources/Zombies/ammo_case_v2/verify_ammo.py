"""Check the ammo case v2 from its files: python verify_ammo.py <project root> [installed]

Size and origin against today's case (worked out from `CreateAmmoCase`'s numbers), faces outward, normals, UVs, textures. Without
"installed" it also checks that nothing uses it yet. Seeing it in s&box is not covered by this.
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
NEW = os.path.join(ASSETS, "models/zombies/ammo_case_v2")
OLD_MIN, OLD_MAX = np.array((-9.0, -12.5, -10.0)), np.array((8.0, 12.5, 20.0))
failures = []
report = {"old_bounds": [OLD_MIN.tolist(), OLD_MAX.tolist()], "lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


for lod in range(3):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"ammo_case_lod{lod}.obj"), encoding="utf-8"):
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
    check(agree > 0.97, f"lod{lod}: only {agree:.3f} of faces agree with their normals")
    check(np.isfinite(v).all() and np.isfinite(vt).all(), f"lod{lod}: non-finite values")
    check(((vt >= -1e-4) & (vt <= 1 + 1e-4)).all(), f"lod{lod}: UVs outside the atlas")
    lo, hi = e.min(0), e.max(0)
    check((lo >= OLD_MIN - 1.0).all() and (hi <= OLD_MAX + 0.5).all(), f"lod{lod}: bounds {lo.round(2)} {hi.round(2)} too far outside the old case's")
    check(abs(lo[2] - OLD_MIN[2]) < 0.1, f"lod{lod}: the bottom moved to {lo[2]}")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), bounds=[lo.round(2).tolist(), hi.round(2).tolist()])

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "ammo_case_lod0.obj"), "ac_chest"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, "solid parts are inside out: " + outward.stdout)

doc = open(os.path.join(NEW, "ammo_case.vmdl"), encoding="utf-8").read()
for ref in re.findall(r'filename = "([^"]+)"', doc) + re.findall(r'to = "([^"]+)"', doc):
    check(os.path.exists(os.path.join(ASSETS, ref)), f"the vmdl names {ref}, which isn't there")
check("PhysicsShapeList" not in doc, "the old case had no physics: this shouldn't gain any")
vmat = open(os.path.join(ASSETS, "materials/zombies/ammo_case_v2/ac_chest.vmat"), encoding="utf-8").read()
for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")

code = open(os.path.join(ROOT, "Code/GameLoop/Rules/Zombies/ZombiesPowerUp.cs"), encoding="utf-8").read()
if INSTALLED:
    check("models/zombies/ammo_case_v2/ammo_case.vmdl" in code, "the code doesn't load v2")
else:
    check("ammo_case_v2" not in code, "the code already loads v2")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
