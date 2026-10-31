"""Check the crates from their files: python verify_crate.py <project root>

Their parts must face outward, they must fit the box collider `railhead_props.crate` gives each (handles stand proud, as a door's
levers do), and every texture a vmat names must exist. Compiling them and seeing them in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/maps/boxyard/shipping_crate_v2")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
failures, report = [], {}
for variant, (length, width, height) in {"standard": (47.2, 31.5, 31.5), "large": (60.0, 48.0, 48.0)}.items():
    report[variant] = {}
    for lod in range(3):
        v, f = [], 0
        for line in open(os.path.join(NEW, f"crate_{variant}_lod{lod}.obj"), encoding="utf-8"):
            if line.startswith("v "):
                v.append(line[2:].split())
            elif line.startswith("f "):
                f += 1
        v = np.array(v, float)[:, [2, 0, 1]]
        lo, hi = v.min(0), v.max(0)
        report[variant][f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
        # Along its length the handles stand proud of the box by up to 1.3 in. Nothing else may.
        if abs(hi[1]) > width / 2 + 0.1 or abs(lo[1]) > width / 2 + 0.1 or hi[0] > length / 2 + 1.3 or lo[0] < -length / 2 - 1.3 or lo[2] < -0.06 or hi[2] > height + 0.2:
            failures.append(f"{variant} lod{lod} is outside its collider: {lo.round(2).tolist()} to {hi.round(2).tolist()}")
    out = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, f"crate_{variant}_lod0.obj"), f"crate_{variant}"], capture_output=True, text=True)
    report[variant]["outward"] = out.stdout.splitlines()[0] if out.stdout else out.stderr
    if out.returncode:
        failures.append(report[variant]["outward"])
    vmat = open(os.path.join(NEW, f"crate_{variant}.vmat"), encoding="utf-8").read()
    for rel in re.findall(r'"([^"]+\.png)"', vmat):
        if not os.path.exists(os.path.join(ASSETS, rel)):
            failures.append(f"missing {rel}")
report["compiled_files"] = sorted(f for f in os.listdir(NEW) if f.endswith("_c"))
report["failures"] = failures
print(json.dumps(report))
sys.exit(1 if failures else 0)
