"""Check the bollard from its files: python verify_bollard.py <project root>

Its parts must face outward, it must fit the box `lowtide_map.mooring_bollard` gives it (9 in round, 25 high), and every texture the vmat names must exist.
As installed: all twelve must be in the scene with no collider, with their old faces gone from the dressing models and their collision boxes where the map's code
says. Seeing it in s&box is `Sources/ReefHall/bench_v2/check_config.py` and `capture_installed.cs.txt`.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/maps/lowtide/mooring_bollard_v2")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
failures, report = [], {}
for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"mooring_bollard_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    radius, low, high = float(np.hypot(v[:, 0], v[:, 1]).max()), float(v[:, 2].min()), float(v[:, 2].max())
    report[f"lod{lod}"] = dict(triangles=f, radius=round(radius, 3), low=round(low, 3), high=round(high, 3))
    if radius > 9.1 or low < -0.05 or high > 25.05:
        failures.append(f"lod{lod} is outside the old box: radius {radius:.2f}, height {low:.2f} to {high:.2f}")
out = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "mooring_bollard_lod0.obj"), "mooring_bollard"], capture_output=True, text=True)
report["outward"] = out.stdout.splitlines()[0] if out.stdout else out.stderr
if out.returncode:
    failures.append(report["outward"])
vmat = open(os.path.join(NEW, "mooring_bollard.vmat"), encoding="utf-8").read()
for rel in re.findall(r'"([^"]+\.png)"', vmat):
    if not os.path.exists(os.path.join(ASSETS, rel)):
        failures.append(f"missing {rel}")
report["compiled_files"] = sorted(f for f in os.listdir(NEW) if f.endswith("_c"))

# As installed. The map's code says where the bollards are.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import lowtide_map as M  # noqa: E402

K = M.K
OLD_N = -1580.0
expected_positions = set()
for side, sign in (("east", 1), ("west", -1)):
    base = os.path.join(ASSETS, "models/maps/lowtide", f"lowtide_dress_{side}")
    spots = M.quay_bollards(sign)
    verts, faces, current = [], [], None
    for line in open(base + ".obj", encoding="utf-8"):
        if line.startswith("v "):
            verts.append(line[2:].split()[:3])
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current == "iron_black":
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    verts = np.array(verts, float)
    # OBJ (a, b, c) is engine (c, a, b), and plan (e, n, z) is engine (n, -e, z).
    east, north, up = -verts[:, 0], verts[:, 2], verts[:, 1]
    left = 0
    for e, n in spots:
        for f in faces:
            if np.hypot(east[f] - e, north[f] - OLD_N).max() < 9.5 and up[f].max() < 25.5:
                left += 1
    if left:
        failures.append(f"{side}: {left} old bollard faces left")
    text = open(base + ".vmdl", encoding="utf-8").read()
    for e, n in spots:
        expected_positions.add(K.vec(K.to_world((e, n, 0.0))))
        origin = f"origin = [ {n:.4f}, {-e:.4f}, 12.5000 ]"
        if text.count(origin) != 1:
            failures.append(f"{side}: no collision box {origin}")
        if n != OLD_N and f"origin = [ {OLD_N:.4f}, {-e:.4f}, 12.5000 ]" in text:
            failures.append(f"{side}: the moved bollard's old collision box is still there")
        # Clear of the crane leg's bogie: its south face is at n -1574.
        if abs(abs(e) - 690) < 1 and n + 9 > -1574:
            failures.append(f"{side}: the bollard at e {e} still reaches the bogie")

# The scene places the model, with no collider.
scene = json.loads(open(M.SCENE_FILE, encoding="utf-8").read())


def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))


placed = [o for o in walk(scene["GameObjects"]) if any(M.BOLLARD_MODEL in str(c.get("Model")) for c in o.get("Components", []))]
report["placed"] = len(placed)
if {o["Position"] for o in placed} != expected_positions or len(placed) != 12:
    failures.append(f"scene bollards differ: {sorted(o['Position'] for o in placed)} against {sorted(expected_positions)}")
if any(c["__type"] != "Sandbox.ModelRenderer" for o in placed for c in o["Components"]):
    failures.append("a placed bollard has a component other than its renderer")
report["failures"] = failures
print(json.dumps(report))
sys.exit(1 if failures else 0)
