"""Check the cooler from its files: python verify_cooler.py <project root> <work dir>

Its bounds must be close to the old cooler's, its parts must face outward, and every file its vmdl and vmat name must exist. On Riverside, the
scene must place it, the old faces must be gone and the pad's collision must be as it was. Seeing it in s&box isn't covered by this:
capture_engine.cs.txt and collision_check.cs.txt do that.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/zombies/cooler_v2")
MATS = os.path.join(ASSETS, "materials/zombies/cooler_v2")
NAME = "cooler"
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def bounds(path):
    v = np.array([line[2:].split()[:3] for line in open(path, encoding="utf-8") if line.startswith("v ")], float)[:, [2, 0, 1]]
    return v.min(0), v.max(0)


# Recorded bounds of the retired box-built cooler; validation doesn't need to retain its obsolete mesh.
old_lo, old_hi = np.array((-16.3, -15.22, 0.0)), np.array((16.3, 8.8, 32.42))
report["old"] = dict(min=old_lo.round(2).tolist(), max=old_hi.round(2).tolist())
for lod in range(3):
    path = os.path.join(NEW, f"{NAME}_lod{lod}.obj")
    lo, hi = bounds(path)
    tris = sum(1 for line in open(path, encoding="utf-8") if line.startswith("f "))
    report[f"lod{lod}"] = dict(triangles=tris, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    # Half an inch either way: the handles and keepers stand a little proud of the old boxes, and the lid's thickness moved.
    check((np.abs(lo - old_lo) <= 0.5).all() and (np.abs(hi - old_hi) <= 0.5).all(), f"lod{lod}: more than half an inch from the old cooler's bounds")
    check(abs(lo[2]) < 0.02, f"lod{lod}: not on the ground")
outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{NAME}_lod0.obj"), NAME], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, f"inside-out parts: {report['outward']}")
vmdl = open(os.path.join(NEW, f"{NAME}.vmdl"), encoding="utf-8").read()
for ref in re.findall(r'filename = "([^"]+)"', vmdl) + re.findall(r'to = "([^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, ref)), f"the vmdl names a missing file: {ref}")
check("PhysicsMeshFile" not in vmdl and "PhysicsHull" not in vmdl, "the vmdl has physics; the map's hull stays the cooler's collision")
vmat = open(os.path.join(MATS, f"{NAME}.vmat"), encoding="utf-8").read()
for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
scene = json.loads(open(os.path.join(ASSETS, "scenes/maps/Riverside/riverside.scene"), encoding="utf-8").read())
placed = [o for o in scene["GameObjects"] if o.get("Name") == "Cooler"]
def model_path(component):
    model = component.get("Model")
    return model.get("Path") if isinstance(model, dict) else model

check(len(placed) == 1 and any(model_path(c) == "models/zombies/cooler_v2/cooler.vmdl"
                             for c in placed[0].get("Components", [])), "the scene doesn't place one new cooler")
report["placed"] = placed[0]["Position"] if placed else None
pad = open(os.path.join(ASSETS, "models/maps/riverside/riverside_pad.obj"), encoding="utf-8").read()
check("usemtl rs_cooler" not in pad, "the old cooler's faces are still in the pad's model")
collision = subprocess.run(["git", "status", "--porcelain", "--", "Assets/models/maps/riverside/*hulls*"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
check(collision == "", f"the pad's collision files changed: {collision}")
# Material remaps can change in another prop task; compare the actual physics blocks, not the whole ModelDoc's status.
def physics_blocks(text):
    blocks = []
    for match in re.finditer(r'_class\s*=\s*"(Physics[^\"]*)"', text):
        start = text.rfind("{", 0, match.start())
        depth = 0
        for end in range(start, len(text)):
            depth += (text[end] == "{") - (text[end] == "}")
            if depth == 0:
                blocks.append(re.sub(r"\s+", "", text[start:end + 1]))
                break
    return blocks

pad_path = "Assets/models/maps/riverside/riverside_pad.vmdl"
baseline = subprocess.run(["git", "show", "HEAD:" + pad_path], cwd=ROOT, capture_output=True, text=True)
check(baseline.returncode == 0, "could not read the pad's committed collision definition")
current = open(os.path.join(ROOT, pad_path), encoding="utf-8").read()
check(physics_blocks(current) == physics_blocks(baseline.stdout), "the pad's physics definition changed")
report["compiled files"] = [n for n in os.listdir(NEW) + os.listdir(MATS) if n.endswith("_c")]
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
