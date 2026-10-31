"""Check the barrier from its files: python verify_jersey.py <project root> <work dir>

LOD 0 must be the right way out, and every LOD must fit the old model's bounds, agree with its normals and stay inside the map's collision
hull, since that hull doesn't change. Every texture the vmat names must exist, and no map file may ask for it yet.
Compiling and seeing it in s&box is not covered by this. OBJ (a, b, c) is engine (c, a, b).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models", "props", "riverdale", "jersey_barrier_v2")
failures = []
report = {"lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


def obj_positions(path):
    return np.array([line[2:].split()[:3] for line in open(path, encoding="utf-8", errors="ignore") if line[:2] == "v "], float)[:, [2, 0, 1]]


old = obj_positions(os.path.join(WORK, "old", "old_barrier.obj"))
old_min, old_max = old.min(0), old.max(0)
report["old_bounds"] = dict(min=old_min.round(3).tolist(), max=old_max.round(3).tolist(), triangles=sum(max(len(line.split()) - 3, 0) for line in open(os.path.join(WORK, "old", "old_barrier.obj"), encoding="utf-8", errors="ignore") if line[:2] == "f "))


def hull_y(z):
    """The old section's half width at a height: the collision hull the map keeps."""
    return np.interp(z, (0.0, 3.0, 10.0, 32.0), (12.0, 12.0, 8.5, 4.75))


for lod in range(4):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"jersey_barrier_lod{lod}.obj"), encoding="utf-8"):
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
    # Collapsing a far LOD moves its corners a little, and at that distance a tenth of an inch can't show. LOD 0 is held tighter.
    check(over < (0.1 if lod == 0 else 0.15), f"lod{lod}: stands {over:.3f} in past the old bounds")
    # Nothing should stand more than a hair outside the hull, or players would see through what stops them.
    outside = float((np.abs(engine[:, 1]) - hull_y(np.clip(engine[:, 2], 0, 32))).max())
    check(outside < 0.2, f"lod{lod}: stands {outside:.3f} in outside the collision hull")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), outside_hull=round(outside, 3), bounds_min=engine.min(0).round(3).tolist(), bounds_max=engine.max(0).round(3).tolist())

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "jersey_barrier_lod0.obj"), "jb_concrete"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, "parts are inside out: " + str(report["outward"]))

vmat = open(os.path.join(NEW, "jb_concrete.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(models/props/riverdale/jersey_barrier_v2/[^"]+\.png)"', vmat)
report["textures"] = len(textures)
check(len(textures) == 5, "the vmat should name five textures")
for tex in textures:
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
vmdl = open(os.path.join(NEW, "jersey_barrier.vmdl"), encoding="utf-8").read()
for path in re.findall(r'"(models/props/riverdale/jersey_barrier_v2/[^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, path)), f"the vmdl names {path}, which is missing")
check(vmdl.count('_class = "LODGroup"') == 4, "the vmdl should have four LOD groups")
for scene in ("riverdale", "spillway"):
    text = open(os.path.join(ASSETS, "scenes", "maps", scene, f"{scene}.scene"), encoding="utf-8", errors="ignore").read()
    check("jersey_barrier_v2" not in text, f"{scene} already uses v2")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
