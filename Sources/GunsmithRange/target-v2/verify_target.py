"""Check the installed range target from its files: python verify_target.py <project root>

Its physics must be the old model's, word for word, and the range must use it and nothing still ask for the old one.
Compiling and seeing it in s&box is not covered by this.
"""
import filecmp
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
OLD = os.path.join(ROOT, "output/asset-improvement-20261030/range-target/retired-range_target")
NEW = os.path.join(ASSETS, "models/gunsmith_range/range_target_v2")
failures = []
report = {"lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


for lod in range(3):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"range_target_lod{lod}.obj"), encoding="utf-8"):
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
    check(agree > 0.985, f"lod{lod}: only {agree:.3f} of faces agree with their normals")
    check(np.isfinite(v).all() and np.isfinite(vt).all(), f"lod{lod}: non-finite values")
    check(abs(engine[:, 2].max() - 73.0) < 0.1, f"lod{lod}: top is not the old model's 73")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), bounds_min=[round(float(x), 2) for x in engine.min(0)], bounds_max=[round(float(x), 2) for x in engine.max(0)])


def physics(doc):
    start = doc.rindex("{", 0, doc.index('_class = "PhysicsShapeList"'))
    end = doc.rindex("]", 0, doc.index("model_archetype"))
    return re.sub(r"\s+", " ", doc[start:end]).strip()


outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "range_target_lod0.obj"), "rt_steel"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, "solid parts are inside out: " + report["outward"])

old_doc = open(os.path.join(OLD, "range_target.vmdl"), encoding="utf-8").read()
new_doc = open(os.path.join(NEW, "range_target.vmdl"), encoding="utf-8").read()
check(physics(old_doc) == physics(new_doc).replace("range_target_v2/", ""), "physics differs from the old model's")
check(filecmp.cmp(os.path.join(OLD, "range_target_hulls_metal.obj"), os.path.join(NEW, "range_target_hulls_metal.obj"), shallow=False), "hulls differ from the old model's")

vmat = open(os.path.join(ASSETS, "materials/gunsmith_range/range_target_v2/rt_steel.vmat"), encoding="utf-8").read()
for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
check('g_flModelTintAmount "1.000"' in vmat, "the hit flash needs the tint on")

scene = open(os.path.join(ASSETS, "scenes/gunsmith_range.scene"), encoding="utf-8").read()
check(scene.count("models/gunsmith_range/range_target_v2/range_target.vmdl") == 8, "the range's four targets don't all use the new model")
check("models/gunsmith_range/range_target.vmdl" not in scene, "the scene still names the old model")
tool = open(os.path.join(ROOT, "Tools/gunsmith_range.py"), encoding="utf-8").read()
check("range_target_v2/range_target.vmdl" in tool and '"range_target",' not in tool, "the generator would bring the old model back")
for name in ("range_target.vmdl", "range_target.obj", "range_target_hulls_metal.obj"):
    check(not os.path.exists(os.path.join(ASSETS, "models/gunsmith_range", name)), f"{name} is still in Assets")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
