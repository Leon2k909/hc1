"""Check the eye wash from its files: python -X utf8 verify_eyewash.py <project root>

Its parts must face outward, it must stay in the space the old one had, within what's around it, and every texture the vmat names must exist. As installed: five in the scene with no collider, where the hall's own
code says, the old faces gone from the hall's detail and fine models, their signs still there, and each compiled model newer than its source. Seeing it in s&box is `installed_config.py` and `capture_compare.cs.txt`.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/maps/riverdale/eyewash_v2")
BASE = os.path.join(ASSETS, "models/maps/riverdale")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
failures, report = [], {}
for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"eyewash_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    if np.abs(v[:, 0]).max() > 10 or lo[1] < -0.05 or hi[1] > 13.3 or lo[2] < 5.2 or hi[2] > 39.5:
        failures.append(f"lod{lod} leaves its space: {lo.round(2).tolist()} to {hi.round(2).tolist()}")
out = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "eyewash_lod0.obj"), "eyewash"], capture_output=True, text=True)
report["outward"] = out.stdout.splitlines()[0] if out.stdout else out.stderr
if out.returncode:
    failures.append(report["outward"])
vmat = open(os.path.join(NEW, "eyewash.vmat"), encoding="utf-8").read()
for rel in re.findall(r'"([^"]+\.png)"', vmat):
    if not os.path.exists(os.path.join(ASSETS, rel)):
        failures.append(f"missing {rel}")

# Where the hall's own code puts them, by running it.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import riverdale_eyewash as E  # noqa: E402
import riverdale_map as M  # noqa: E402

M.P.reset()
M.H.build()
placed = list(E.PLACED)
report["from_the_code"] = [(np.round(p, 2).tolist(), round(y, 1)) for p, y in placed]
if len(placed) != 5:
    failures.append(f"the hall records {len(placed)} eye washes, not 5")

scene = json.loads(open(M.SCENE_FILE, encoding="utf-8").read())
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
group = next((c for c in world["Children"] if c.get("Name") == "Eye Washes"), None)
if group is None:
    failures.append("no Eye Washes group in the scene")
else:
    expected = E.scene_group(M.ids, placed)
    got = {c["__guid"]: c for c in group["Children"]}
    for c in expected["Children"]:
        if c["__guid"] not in got or json.dumps(got[c["__guid"]], sort_keys=True) != json.dumps(c, sort_keys=True):
            failures.append(f"the scene's eye wash differs from the code's at {c['Position']}")
    if len(got) != len(expected["Children"]):
        failures.append(f"{len(got)} in the scene against {len(expected['Children'])} from the code")
    if any(k["__type"] != "Sandbox.ModelRenderer" for c in group["Children"] for k in c["Components"]):
        failures.append("an eye wash has a component other than its renderer")

# The old faces are gone from the live models, and the signs stayed.
OLD = {"rv_hall_green", "rv_stainless", "rv_hall_chrome"}
for name in ("riverdale_hall_detail", "riverdale_hall_fine"):
    verts, faces, material = [], [], None
    for line in open(os.path.join(BASE, name + ".obj"), encoding="utf-8"):
        if line.startswith("v "):
            verts.append(line[2:].split()[:3])
        elif line.startswith("usemtl"):
            material = line.split()[1]
        elif line.startswith("f "):
            faces.append((material, [int(t.split("/")[0]) - 1 for t in line.split()[1:]]))
    verts = np.array(verts, float)
    x, y, z = verts[:, 2], verts[:, 0], verts[:, 1]
    left = signs = 0
    for (px, py, _), _yaw in placed:
        near = np.hypot(x - px, y - py) < 14
        for material, f in faces:
            if near[f].all():
                if material in OLD and z[f].min() >= 5.9 and z[f].max() <= 38.8:
                    left += 1
                if material == "rv_hall_signs" and z[f].min() > 45:
                    signs += 1
    report[name] = dict(old_faces_left=left, sign_faces=signs)
    if left:
        failures.append(f"{name}: {left} old faces left")
    if name.endswith("fine") and signs < 10:
        failures.append(f"{name}: only {signs} sign faces over the eye washes")
    source, compiled = os.path.join(BASE, name + ".obj"), os.path.join(BASE, name + ".vmdl_c")
    if os.path.getmtime(compiled) < os.path.getmtime(source):
        failures.append(f"{name}.vmdl_c is older than its OBJ, so the game still draws the old one")
report["failures"] = failures
print(json.dumps(report))
sys.exit(1 if failures else 0)
