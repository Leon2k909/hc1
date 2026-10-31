"""Check the drum from its files: python verify_drum.py <project root> <work dir>

Its bounds must match the old drum's, its parts must face outward and every file its vmdls and vmats name must exist. On Riverside, all
14 must be placed, the old faces gone, and the hulls and fires as they were. Compiling it and seeing it in s&box are not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/zombies/burn_drum_v2")
MATS = os.path.join(ASSETS, "materials/zombies/burn_drum_v2")
NAME = "burn_drum"
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def bounds(path):
    """Radius from the axis, lowest and highest point. Radius, since the old drum's 14 sides are narrower across some axes."""
    v = np.array([line[2:].split()[:3] for line in open(path, encoding="utf-8") if line.startswith("v ")], float)[:, [2, 0, 1]]
    return float(np.hypot(v[:, 0], v[:, 1]).max()), float(v[:, 2].min()), float(v[:, 2].max())


old_r, old_lo, old_hi = bounds(os.path.join(WORK, "old_drum.obj"))
report["old"] = dict(radius=round(old_r, 3), bottom=round(old_lo, 3), top=round(old_hi, 3))
for lod in range(3):
    path = os.path.join(NEW, f"{NAME}_lod{lod}.obj")
    r, lo, hi = bounds(path)
    tris = sum(1 for line in open(path, encoding="utf-8") if line.startswith("f "))
    report[f"lod{lod}"] = dict(triangles=tris, radius=round(r, 3), bottom=round(lo, 3), top=round(hi, 3))
    check(r <= old_r + 0.1, f"lod{lod}: wider than the old drum")
    check(abs(lo) < 0.02 and abs(hi - old_hi) < 0.2, f"lod{lod}: not the old drum's height, or not on the ground")
outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{NAME}_lod0.obj"), NAME], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, f"inside-out parts: {report['outward']}")
report["materials"] = {}
for variant in ("blue", "red", "rust", "cold"):
    vmdl = open(os.path.join(NEW, f"{NAME}_{variant}.vmdl"), encoding="utf-8").read()
    for ref in re.findall(r'filename = "([^"]+)"', vmdl) + re.findall(r'to = "([^"]+)"', vmdl):
        check(os.path.exists(os.path.join(ASSETS, ref)), f"{variant}: the vmdl names a missing file: {ref}")
    check("PhysicsMeshFile" not in vmdl and "PhysicsHull" not in vmdl, f"{variant}: the vmdl has physics; the map's hull stays the drum's collision")
    vmat = open(os.path.join(MATS, f"{NAME}_{variant}.vmat"), encoding="utf-8").read()
    textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
    report["materials"][variant] = len(textures)
    for tex in textures:
        check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
    check(("F_SELF_ILLUM" in vmat) == (variant != "cold"), f"{variant}: glow is the wrong way round")
scene = json.loads(open(os.path.join(ASSETS, "scenes/maps/Riverside/riverside.scene"), encoding="utf-8").read())
group = next((o for o in scene["GameObjects"] if o.get("Name") == "Burn Drums"), None)
check(group is not None, "the scene has no Burn Drums group")
placed = group["Children"] if group else []
report["placed"] = len(placed)
check(len(placed) == 14, f"{len(placed)} drums in the scene, not 14")
for drum in placed:
    model = drum["Components"][0]["Model"]
    check(os.path.exists(os.path.join(ASSETS, model)), f"{drum['Name']}: missing {model}")
fires = next((o for o in scene["GameObjects"] if o.get("Name") == "Fires"), {"Children": []})
report["drum fires"] = sum(1 for f in fires["Children"] if "drum" in f["Name"])
check(report["drum fires"] == 12, "the 12 burning drums' fires aren't all there")
hulls = subprocess.run(["git", "status", "--porcelain", "--", "Assets/models/maps/riverside/*hulls*"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
check(hulls == "", f"Riverside's hulls changed: {hulls}")
for zone in ("riverside_pad", "riverside_store", "riverside_dressing"):
    text = open(os.path.join(ASSETS, f"models/maps/riverside/{zone}.obj"), encoding="utf-8").read()
    # Not rs_drum_red: other things are painted with it, like the old cooler's cans on the pad.
    check("usemtl rs_ember" not in text and "usemtl rs_drum_blue" not in text, f"{zone}: old drum faces are still there")
report["compiled files"] = [n for n in os.listdir(NEW) + os.listdir(MATS) if n.endswith("_c")]
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
