"""Check the cabinet from its files: python -X utf8 verify_first_aid.py <project root>

Its parts must face outward, it must cover the old box's 14 x 17 x 5, and every texture the vmat names must exist. As installed: the scene must place it at the four spots, the old faces must be gone from
the hall's detail and fine models, the signs atlas must still be there for the hall's other signs, and each compiled model must be newer than its source. Seeing it is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/maps/riverdale/first_aid_v2")
BASE = os.path.join(ASSETS, "models/maps/riverdale")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
failures, report = [], {}
for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"first_aid_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    if lo[0] < -0.01 or hi[0] < 5.05 or lo[1] > -7.0 or hi[1] < 7.0 or lo[2] > 0.0 or hi[2] < 17.0:
        failures.append(f"lod{lod} doesn't cover the old box: {lo.round(2).tolist()} to {hi.round(2).tolist()}")
out = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "first_aid_lod0.obj"), "first_aid"], capture_output=True, text=True)
report["outward"] = out.stdout.splitlines()[0] if out.stdout else out.stderr
if out.returncode:
    failures.append(report["outward"])
vmat = open(os.path.join(NEW, "first_aid.vmat"), encoding="utf-8").read()
for rel in re.findall(r'"([^"]+\.png)"', vmat):
    if not os.path.exists(os.path.join(ASSETS, rel)):
        failures.append(f"missing {rel}")

scene = json.loads(open(os.path.join(ASSETS, "scenes/maps/Riverdale/riverdale.scene"), encoding="utf-8").read())
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
group = next((c for c in world["Children"] if c.get("Name") == "First Aid Cabinets"), None)
report["placed"] = [c["Position"] for c in group["Children"]] if group else []
if sorted(report["placed"]) != sorted(["985,1000,54", "985,-1000,54", "2000,962,54", "2000,95,54"]):
    failures.append(f"the scene places {report['placed']}")

SPOTS = (((-1000.0, 985.0), (1.0, 0.0)), ((1000.0, 985.0), (-1.0, 0.0)), ((-962.0, 2000.0), (0.0, -1.0)), ((-95.0, 2000.0), (0.0, -1.0)))
for name, paint, limit, near, far in (("riverdale_hall_detail.obj", "rv_hall_green", 7.02, -0.01, 5.02), ("riverdale_hall_fine.obj", "rv_hall_signs", 6.42, 5.0, 5.1)):
    lines = open(os.path.join(BASE, name), encoding="utf-8").read().splitlines()
    v = np.array([l[2:].split()[:3] for l in lines if l.startswith("v ")], float)
    east, north, up = -v[:, 0], v[:, 2], v[:, 1]
    current, left, others = None, 0, 0
    for line in lines:
        if line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current == paint:
            others += 1
            f = np.array([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
            if up[f].min() < 53.9 or up[f].max() > 71.1:
                continue
            for (e, n), (oe, on) in SPOTS:
                o = (east[f] - e) * oe + (north[f] - n) * on
                a = (east[f] - e) * -on + (north[f] - n) * oe
                if np.abs(a).max() <= limit and o.min() >= near and o.max() <= far:
                    left += 1
    report[name] = dict(old_faces_left=left, other_faces_of_that_paint=others)
    if left:
        failures.append(f"{name} still has {left} of the old faces")
    # The eye washes took the rest of rv_hall_green from the detail model, but the signs atlas serves the hall's other signs.
    if paint == "rv_hall_signs" and not others:
        failures.append(f"{name} has lost all of {paint}, which other things use")
report["waiting_for_the_editor_to_compile"] = []
for stem in ("riverdale_hall_detail", "riverdale_hall_fine"):
    src = max(os.path.getmtime(os.path.join(BASE, stem + ext)) for ext in (".obj", ".vmdl"))
    if os.path.getmtime(os.path.join(BASE, stem + ".vmdl_c")) < src:
        report["waiting_for_the_editor_to_compile"].append(stem)
report["failures"] = failures
print(json.dumps(report))
sys.exit(1 if failures else 0)
