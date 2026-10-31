"""Check rifle suppressor v2 from its files: python verify_suppressor.py <project root>

LOD 0 must be the right way out, every LOD must fit the old model's bounds and agree with its normals, every texture the vmat
names must exist, and the prefab and audit tool must ask for v2. Compiling and seeing it in s&box is not covered by this.
OBJ (a, b, c) is engine (c, a, b).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
HC1 = os.path.join(ASSETS, "attachments", "hc1")
NEW = os.path.join(HC1, "rifle_suppressor_v2")
failures = []
report = {"lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


old = np.array([line[2:].split()[:3] for line in open(os.path.join(HC1, "rifle_suppressor", "rifle_suppressor.obj"), encoding="utf-8", errors="ignore") if line[:2] == "v "], float)[:, [2, 0, 1]]
old_min, old_max = old.min(0), old.max(0)
report["old_bounds"] = dict(min=old_min.round(3).tolist(), max=old_max.round(3).tolist())

for lod in range(4):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"rifle_suppressor_lod{lod}.obj"), encoding="utf-8"):
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
    engine = v[:, [2, 0, 1]]
    check(agree > 0.97, f"lod{lod}: only {agree:.3f} of faces agree with their normals")
    check(np.isfinite(v).all() and np.isfinite(vt).all(), f"lod{lod}: non-finite values")
    check((vt >= 0).all() and (vt <= 1).all(), f"lod{lod}: UVs outside the atlas")
    if lod == 0:
        check(abs(engine[:, 0].min() - old_min[0]) < 0.02 and abs(engine[:, 0].max() - old_max[0]) < 0.02, f"lod0: length {engine[:, 0].min():.3f}..{engine[:, 0].max():.3f} differs from the old")
        check(np.abs(engine[:, 1:]).max() < 0.83, f"lod0: radius {np.abs(engine[:, 1:]).max():.3f} is past the old model's")
    else:
        check((engine.min(0) > old_min - 0.03).all() and (engine.max(0) < old_max + 0.03).all(), f"lod{lod}: outside the old bounds")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), bounds_min=engine.min(0).round(3).tolist(), bounds_max=engine.max(0).round(3).tolist())

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "rifle_suppressor_lod0.obj"), "rs_can"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, "parts are inside out: " + str(report["outward"]))

vmat = open(os.path.join(NEW, "rs_can.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(attachments/hc1/rifle_suppressor_v2/[^"]+\.png)"', vmat)
report["textures"] = textures
check(len(textures) == 5, "the vmat should name five textures")
for tex in textures:
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
vmdl = open(os.path.join(NEW, "rifle_suppressor.vmdl"), encoding="utf-8").read()
for path in re.findall(r'"(attachments/hc1/rifle_suppressor_v2/[^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, path)), f"the vmdl names {path}, which is missing")
check(vmdl.count('_class = "LODGroup"') == 4, "the vmdl should have four LOD groups")

prefab = open(os.path.join(ASSETS, "gunsmith", "hc1", "rifle_suppressor", "rifle_suppressor.prefab"), encoding="utf-8").read()
check("attachments/hc1/rifle_suppressor_v2/rifle_suppressor.vmdl" in prefab, "the prefab doesn't use v2")
check("attachments/hc1/rifle_suppressor/rifle_suppressor.vmdl" not in prefab, "the prefab still names the old model")
audit = open(os.path.join(ROOT, "Editor", "Hc1AttachmentAudit.cs"), encoding="utf-8").read()
check("attachments/hc1/rifle_suppressor_v2/rifle_suppressor.vmdl" in audit, "the audit tool doesn't check v2")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
