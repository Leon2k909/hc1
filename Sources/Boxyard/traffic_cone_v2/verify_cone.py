"""Check the cone from its files: python verify_cone.py <project root> <work dir>

Its parts must face outward, it must stay within the old cone's size, and every file its vmdl and vmat name must exist. Seeing it in
s&box is covered by match_view.cs.txt, collision_check.cs.txt and walk_check.cs.txt, run in a match.
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
HALF, HEIGHT = 7.0, 28.0  # boxyard_map.cone
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"traffic_cone_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(3).tolist(), max=hi.round(3).tolist())
    check(max(abs(lo[:2]).max(), abs(hi[:2]).max()) <= HALF + 0.02, f"lod{lod}: base stands past the old one's {HALF}")
    check(abs(hi[2] - HEIGHT) < 0.05 and abs(lo[2]) < 0.02, f"lod{lod}: height runs {lo[2]:.3f} to {hi[2]:.3f}, the old cone's to {HEIGHT}")
outward = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "traffic_cone_lod0.obj"), "traffic_cone"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, f"outward: {report['outward']}")

vmdl = open(os.path.join(NEW, "traffic_cone.vmdl"), encoding="utf-8").read()
for rel in re.findall(r'filename = "([^"]+)"', vmdl):
    check(os.path.exists(os.path.join(NEW, os.path.basename(rel))), f"missing {rel}")
vmat = open(os.path.join(NEW, "traffic_cone.vmat"), encoding="utf-8").read()
textures = re.findall(r'"([^"]+\.png)"', vmat)
check(len(textures) == 4, f"{len(textures)} textures")
for rel in textures:
    check(os.path.exists(os.path.join(NEW, os.path.basename(rel))), f"missing {rel}")

report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
