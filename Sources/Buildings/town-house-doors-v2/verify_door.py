"""Check the doors from their files: python verify_door.py <project root>

The leaf must fill the prefab's collider, its parts must face outward, its textures must exist, and the old doors and the
prefab must be as they were. Compiling and seeing them in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/buildings/town_house/door_v2")
LEAF = {"outer": (-0.875, 44.75, -41.625, 43.75), "inner": (-0.6875, 38.9375, -41.625, 39.75)}
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


for variant, (y0, y1, z0, z1) in LEAF.items():
    name = f"door_{variant}"
    report[name] = {}
    for lod in range(3):
        v, f = [], 0
        for line in open(os.path.join(NEW, f"{name}_lod{lod}.obj"), encoding="utf-8"):
            if line.startswith("v "):
                v.append(line[2:].split())
            elif line.startswith("f "):
                f += 1
        v = np.array(v, float)[:, [2, 0, 1]]
        lo, hi = v.min(0), v.max(0)
        report[name][f"lod{lod}"] = dict(triangles=f, min=[round(float(x), 2) for x in lo], max=[round(float(x), 2) for x in hi])
        check(abs(hi[2] - z1) < 0.3 and abs(lo[2] - z0) < 0.3, f"{name} lod{lod}: height doesn't match the collider")
        check(abs(hi[1] - y1) < 0.3, f"{name} lod{lod}: width doesn't match the collider")
    outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{name}_lod0.obj"), name], capture_output=True, text=True)
    report[name]["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
    check(outward.returncode == 0, f"{name}: {report[name]['outward']}")
    vmat = open(os.path.join(ASSETS, f"materials/buildings/town_house_door_v2/{name}.vmat"), encoding="utf-8").read()
    for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
        check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
tracked = subprocess.run(["git", "status", "--porcelain", "--", "Assets/models/buildings/town_house/town_house_door_outer.obj", "Assets/models/buildings/town_house/town_house_door_outer.vmdl", "Assets/models/buildings/town_house/town_house_door_inner.obj", "Assets/models/buildings/town_house/town_house_door_inner.vmdl", "Assets/prefabs/buildings/town_house.prefab"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
check(tracked == "", f"old doors or the prefab changed: {tracked}")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
