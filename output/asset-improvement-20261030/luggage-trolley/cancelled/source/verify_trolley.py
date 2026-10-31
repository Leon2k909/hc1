"""Check the trolley from its files: python verify_trolley.py <project root>

Its parts must face outward, its bounds must match the old model's, its physics must be the old model's word for word, its
textures must exist, and the old model and the map must be as they were. Compiling and seeing it in s&box is not covered.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
OLD = os.path.join(ASSETS, "models/props/railhead/luggage")
NEW = os.path.join(ASSETS, "models/props/railhead/luggage_trolley_v2")
MATS = "materials/railhead/luggage_trolley_v2"
NAME = "luggage_trolley"
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
    v = np.array(v, float)[:, [2, 0, 1]]  # OBJ (a, b, c) is engine (c, a, b).
    return v, f


def physics(path):
    text = open(path, encoding="utf-8").read()
    start = text.index('_class = "PhysicsShapeList"')
    block = text[start : text.index("]", text.rindex('_class = "Physics'))]
    return re.sub(r"\s+", " ", block.replace("models/props/railhead/luggage_trolley_v2/", "models/props/railhead/luggage/"))


old_v, old_f = read_obj(os.path.join(OLD, f"{NAME}.obj"))
lo0, hi0 = old_v.min(0), old_v.max(0)
report["old"] = dict(triangles=old_f, min=lo0.round(2).tolist(), max=hi0.round(2).tolist())
for lod in range(4):
    v, f = read_obj(os.path.join(NEW, f"{NAME}_lod{lod}.obj"))
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    if lod == 0:
        check(np.abs(lo - lo0).max() < 0.5 and np.abs(hi - hi0).max() < 0.5, f"lod0 bounds differ from the old model's by more than 0.5 in: {lo} {hi}")
    if lod < 3:
        check(np.abs(lo[2] - lo0[2]) < 0.5, f"lod{lod}: doesn't reach the ground")
    if lod:
        check(f < report[f"lod{lod - 1}"]["triangles"], f"lod{lod} isn't lighter than lod{lod - 1}")

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{NAME}_lod0.obj"), NAME], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, report["outward"])

check(physics(os.path.join(OLD, f"{NAME}.vmdl")) == physics(os.path.join(NEW, f"{NAME}.vmdl")), "physics differs from the old model's")
for hull in ("cloth", "rubber"):
    a = open(os.path.join(OLD, f"{NAME}_hulls_{hull}.obj"), "rb").read()
    b = open(os.path.join(NEW, f"{NAME}_hulls_{hull}.obj"), "rb").read()
    check(hashlib.sha1(a).digest() == hashlib.sha1(b).digest(), f"{hull} hull differs")

vmat = open(os.path.join(ASSETS, MATS, f"{NAME}.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
report["textures"] = textures
check(len(textures) == 5, "expected five textures")
for tex in textures:
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")

vmdl = open(os.path.join(NEW, f"{NAME}.vmdl"), encoding="utf-8").read()
for name in re.findall(r'filename = "([^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, name)), f"vmdl names missing file {name}")
check(f'to = "{MATS}/{NAME}.vmat"' in vmdl, "vmdl doesn't remap to the new material")

compiled = [f for d in (NEW, os.path.join(ASSETS, MATS)) for f in os.listdir(d) if f.endswith("_c")]
report["compiled_files"] = compiled
tracked = subprocess.run(["git", "status", "--porcelain", "--", "Assets/models/props/railhead/luggage", "Assets/materials/railhead/luggage", "Tools/railhead_luggage.py", "Assets/scenes/maps/Railhead/railhead.scene"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
check(tracked == "", f"old model or the map changed: {tracked}")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
