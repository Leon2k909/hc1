"""Check the bench from its files: python verify_bench.py <project root> <work dir>

LOD 0 must be the right way out, every LOD must fit the old model's bounds and agree with its normals, every texture the vmat names must
exist, and no map file may ask for it yet. Compiling and seeing it in s&box is not covered by this. OBJ (a, b, c) is engine (c, a, b).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models", "props", "cerroblanco", "bench_v2")
failures = []
report = {"lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


old_path = os.path.join(WORK, "old", "old_bench.obj")
old = np.array([line[2:].split()[:3] for line in open(old_path, encoding="utf-8", errors="ignore") if line[:2] == "v "], float)[:, [2, 0, 1]]
old_min, old_max = old.min(0), old.max(0)
report["old"] = dict(min=old_min.round(3).tolist(), max=old_max.round(3).tolist(), triangles=sum(max(len(line.split()) - 3, 0) for line in open(old_path, encoding="utf-8", errors="ignore") if line[:2] == "f "))

for lod in range(4):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"bench_lod{lod}.obj"), encoding="utf-8"):
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
    over = max(float((old_min - engine.min(0)).max()), float((engine.max(0) - old_max).max()))
    check(over < 0.05, f"lod{lod}: stands {over:.3f} in past the old bounds")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), past_old=round(over, 3), bounds_min=engine.min(0).round(3).tolist(), bounds_max=engine.max(0).round(3).tolist())

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "bench_lod0.obj"), "bn_bench"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, "parts are inside out: " + str(report["outward"]))

vmat = open(os.path.join(NEW, "bn_bench.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(models/props/cerroblanco/bench_v2/[^"]+\.png)"', vmat)
check(len(textures) == 5, "the vmat should name five textures")
for tex in textures:
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
vmdl = open(os.path.join(NEW, "bench.vmdl"), encoding="utf-8").read()
for path in re.findall(r'"(models/props/cerroblanco/bench_v2/[^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, path)), f"the vmdl names {path}, which is missing")
check(vmdl.count('_class = "LODGroup"') == 4, "the vmdl should have four LOD groups")
scene = open(os.path.join(ASSETS, "scenes", "maps", "cerroblanco", "cerroblanco.scene"), encoding="utf-8", errors="ignore").read()
check("bench_v2" not in scene, "the map already uses v2")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
