"""Check the wheelie bin from its files: python verify_bin.py <project root> <work dir>

Its parts must face outward, it must stay close to the size `boxyard_map.wheelie_bin` makes one, each colour's vmdl and vmat must
name files that exist, and Boxyard must not be using it yet. Compiling it and seeing it in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
NEW = os.path.join(WORK, "export")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
FOLDER = "models/maps/boxyard/wheelie_bin_v2"
OLD_LOW, OLD_HIGH = np.array((-12.0, -16.5, 0.0)), np.array((12.0, 16.0, 42.2))  # What boxyard_map's collision box covers.
LIMIT = 0.25  # Inches it may stand past that.
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
    return np.array(v, float)[:, [2, 0, 1]], f


for lod in range(3):
    v, f = read_obj(os.path.join(NEW, f"wheelie_bin_lod{lod}.obj"))
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(3).tolist(), max=hi.round(3).tolist())
    over = max(float((OLD_LOW - lo).max()), float((hi - OLD_HIGH).max()))
    check(over < LIMIT, f"lod{lod} stands {over:.3f} in past the old size")
outward = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "wheelie_bin_lod0.obj"), "wheelie_bin"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, str(report["outward"]))

for colour in ("green", "grey", "blue"):
    vmdl = open(os.path.join(NEW, f"wheelie_bin_{colour}.vmdl"), encoding="utf-8").read()
    for rel in re.findall(r'filename = "([^"]+)"', vmdl):
        check(rel.startswith(FOLDER + "/") and os.path.exists(os.path.join(NEW, os.path.basename(rel))), f"{colour}: missing {rel}")
    vmat_rel = re.search(r'to = "([^"]+\.vmat)"', vmdl).group(1)
    vmat = open(os.path.join(NEW, os.path.basename(vmat_rel)), encoding="utf-8").read()
    for rel in re.findall(r'"([^"]+\.png)"', vmat):
        check(os.path.exists(os.path.join(NEW, os.path.basename(rel))), f"{colour}: missing {rel}")

scene = open(os.path.join(ROOT, "Assets/scenes/maps/Boxyard/boxyard.scene"), encoding="utf-8").read()
if "installed" in sys.argv[3:]:
    check(scene.count("wheelie_bin_v2") == 3, "Boxyard doesn't place all three")
else:
    check("wheelie_bin_v2" not in scene, "Boxyard already uses it")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
