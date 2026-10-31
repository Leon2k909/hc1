"""Check the teddy from its files: python verify_teddy.py <project root> <work dir>

Its parts must face outward, it must stand on the ground at about the old one's height and stay close to its footprint, every file its vmdl and vmat name must
exist, and it must have no physics, as the old one had none. On Riverside, the scene must place it and the old faces must be gone. Seeing it in s&box isn't covered by this: capture_installed.cs.txt does that.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/zombies/teddy_v2")
MATS = os.path.join(ASSETS, "materials/zombies/teddy_v2")
NAME = "teddy"
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def bounds(path):
    v = np.array([line[2:].split()[:3] for line in open(path, encoding="utf-8") if line.startswith("v ")], float)[:, [2, 0, 1]]
    return v.min(0), v.max(0)


old_lo, old_hi = bounds(os.path.join(WORK, "old_teddy.obj"))
report["old"] = dict(min=old_lo.round(2).tolist(), max=old_hi.round(2).tolist())
for lod in range(3):
    path = os.path.join(NEW, f"{NAME}_lod{lod}.obj")
    lo, hi = bounds(path)
    tris = sum(1 for line in open(path, encoding="utf-8") if line.startswith("f "))
    report[f"lod{lod}"] = dict(triangles=tris, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    # A tenth of an inch: decimating moves points, and a dip that small is lost in the mud it sits in.
    check(abs(lo[2]) <= 0.1, f"lod{lod}: not on the ground")
    check(abs(hi[2] - old_hi[2]) < 2.0, f"lod{lod}: more than 2 in from the old one's height")
    # Its legs stick out in front, which is the reason for the room: the old one's stopped short.
    check(hi[0] <= old_hi[0] + 5.0 and lo[0] >= old_lo[0] - 2.0 and np.abs(lo[1]).max() <= 9.5 and hi[1] <= 9.5, f"lod{lod}: too far outside the old one's footprint")
outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{NAME}_lod0.obj"), NAME], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, f"inside-out parts: {report['outward']}")
vmdl = open(os.path.join(NEW, f"{NAME}.vmdl"), encoding="utf-8").read()
for ref in re.findall(r'filename = "([^"]+)"', vmdl) + re.findall(r'to = "([^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, ref)), f"the vmdl names a missing file: {ref}")
check("PhysicsMeshFile" not in vmdl and "PhysicsHull" not in vmdl, "the vmdl has physics, and the old teddy had none")
vmat = open(os.path.join(MATS, f"{NAME}.vmat"), encoding="utf-8").read()
for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
scene = json.loads(open(os.path.join(ASSETS, "scenes/maps/Riverside/riverside.scene"), encoding="utf-8").read())
placed = [o for o in scene["GameObjects"] if o.get("Name") == "Teddy"]
check(len(placed) == 1 and placed[0]["Components"][0]["Model"] == "models/zombies/teddy_v2/teddy.vmdl", "the scene doesn't place one new teddy")
report["placed"] = placed[0]["Position"] if placed else None
pad = open(os.path.join(ASSETS, "models/maps/riverside/riverside_pad.obj"), encoding="utf-8").read()
check("usemtl rs_teddy" not in pad, "the old teddy's faces are still in the pad's model")
report["compiled files"] = [n for n in os.listdir(NEW) + os.listdir(MATS) if n.endswith("_c")]
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
