"""Check the power-up drops v2 from their files: python verify_powerups.py <project root> [installed]

Each must fit the old 15-inch cube about the same origin, face outward and have every file it names. Without "installed" it
also checks that nothing uses them yet. Seeing them in s&box is not covered by this.
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
NEW = os.path.join(ASSETS, "models/zombies/powerups_v2")
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


for name, mat in (("powerup_one_hit", "pu_one_hit"), ("powerup_clean_sweep", "pu_clean_sweep")):
    entry = {"lods": {}}
    for lod in range(3):
        v, vt, vn, f = [], [], [], []
        for line in open(os.path.join(NEW, f"{name}_lod{lod}.obj"), encoding="utf-8"):
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
        check(agree > 0.97, f"{name} lod{lod}: only {agree:.3f} of faces agree with their normals")
        check(np.isfinite(v).all() and np.isfinite(vt).all(), f"{name} lod{lod}: non-finite values")
        check(((vt >= -1e-4) & (vt <= 1 + 1e-4)).all(), f"{name} lod{lod}: UVs outside the atlas")
        check((lo >= -7.55).all() and (hi <= 7.55).all(), f"{name} lod{lod}: outside the old 15-inch cube: {lo.round(2)} {hi.round(2)}")
        entry["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), bounds=[lo.round(2).tolist(), hi.round(2).tolist()])
    outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{name}_lod0.obj"), mat], capture_output=True, text=True)
    entry["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
    check(outward.returncode == 0, f"{name}: inside out: " + outward.stdout)
    doc = open(os.path.join(NEW, name + ".vmdl"), encoding="utf-8").read()
    for ref in re.findall(r'filename = "([^"]+)"', doc) + re.findall(r'to = "([^"]+)"', doc):
        check(os.path.exists(os.path.join(ASSETS, ref)), f"{name}.vmdl names {ref}, which isn't there")
    check("PhysicsShapeList" not in doc, f"{name}: the old cube had no physics on the drop")
    vmat = open(os.path.join(ASSETS, "materials/zombies/powerups_v2", mat + ".vmat"), encoding="utf-8").read()
    for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
        check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
    report[name] = entry

code = open(os.path.join(ROOT, "Code/GameLoop/Rules/Zombies/ZombiesPowerUp.cs"), encoding="utf-8").read()
if INSTALLED:
    check("powerups_v2" in code, "the code doesn't load them")
else:
    check("powerups_v2" not in code, "the code already loads them")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
