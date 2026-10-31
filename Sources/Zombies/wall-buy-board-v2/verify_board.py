"""Check the board from its files: python verify_board.py <project root>

The whole model must stay inside the station's collider, its parts must face outward and its textures must exist. It also
reports whether the Zombies code has uncommitted changes and which compiled files exist. Compiling it and seeing it in s&box
are not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/zombies/wall_buy_board_v2")
NAME = "wall_buy_board"
# Board-local: the old board's centre is the origin. The station's collider is x -5..5, y +-30, z 0..60 in station space.
OLD = np.array(((-1.0, -30.0, -20.0), (1.0, 30.0, 20.0)))
COLLIDER = np.array(((-1.0, -30.0, -40.0), (9.0, 30.0, 20.0)))
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"{NAME}_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=[round(float(x), 3) for x in lo], max=[round(float(x), 3) for x in hi])
    check((lo >= COLLIDER[0] - 0.02).all() and (hi <= COLLIDER[1] + 0.02).all(), f"lod{lod}: outside the station's collider")
    check(abs(hi[1] - 30) < 0.02 and abs(lo[1] + 30) < 0.02, f"lod{lod}: not the old board's width")
    check(abs(hi[2] - 20) < 0.02 and abs(lo[2] + 40) < 0.02, f"lod{lod}: doesn't run from the floor to the old board's top")
report["old board"] = dict(min=OLD[0].tolist(), max=OLD[1].tolist())
report["station collider"] = dict(min=COLLIDER[0].tolist(), max=COLLIDER[1].tolist())
outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{NAME}_lod0.obj"), NAME], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, f"inside-out parts: {report['outward']}")
vmat = open(os.path.join(ASSETS, f"materials/zombies/wall_buy_board_v2/{NAME}.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
report["textures"] = textures
for tex in textures:
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
vmdl = open(os.path.join(NEW, f"{NAME}.vmdl"), encoding="utf-8").read()
for ref in re.findall(r'filename = "([^"]+)"', vmdl) + re.findall(r'to = "([^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, ref)), f"the vmdl names a missing file: {ref}")
check("PhysicsMeshFile" not in vmdl and "PhysicsHull" not in vmdl, "the vmdl has physics; the old board's station uses only its BoxCollider")
tracked = subprocess.run(["git", "status", "--porcelain", "--", "Code/GameLoop/Rules/Zombies"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
report["zombies code"] = tracked or "unchanged"
compiled = [n for n in os.listdir(NEW) if n.endswith("_c")] + [n for n in os.listdir(os.path.dirname(os.path.join(ASSETS, textures[0]))) if n.endswith("_c")]
report["compiled files"] = compiled
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
