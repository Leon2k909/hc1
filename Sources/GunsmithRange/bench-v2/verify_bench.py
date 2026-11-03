"""Check the bench from its files: python verify_bench.py <project root>

Its parts must face outward, its frame and top must fit the old bench's 170 x 30 x 34 (only the rests, brass and ear defenders may stand outside that), every texture
the vmat names must exist, the range's scene must place it on all four lanes and the range's own model must no longer draw the old one. Compiling it and seeing it in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/gunsmith_range/shooting_bench_v2")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
failures, report = [], {}
for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"bench_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    if abs(lo[1]) > 85.2 or hi[1] > 85.2 or lo[2] < -0.05:
        failures.append(f"lod{lod} is longer than the old bench: {lo.round(2).tolist()} to {hi.round(2).tolist()}")
out = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "bench_lod0.obj"), "bench"], capture_output=True, text=True)
report["outward"] = out.stdout.splitlines()[0] if out.stdout else out.stderr
if out.returncode:
    failures.append(report["outward"])
vmat = open(os.path.join(NEW, "bench.vmat"), encoding="utf-8").read()
for rel in re.findall(r'"([^"]+\.png)"', vmat):
    if not os.path.exists(os.path.join(ASSETS, rel)):
        failures.append(f"missing {rel}")
scene = open(os.path.join(ASSETS, "scenes/gunsmith_range.scene"), encoding="utf-8").read()
if scene.count("models/gunsmith_range/shooting_bench_v2/bench.vmdl") != 4:
    failures.append("The range's scene should place the bench four times.")
if "bench_oak" in open(os.path.join(ASSETS, "models/gunsmith_range/gunsmith_range.obj"), encoding="utf-8").read():
    failures.append("The range's own model still draws the old bench.")
report["failures"] = failures
print(json.dumps(report))
sys.exit(1 if failures else 0)
