"""Check the information stand from its files: python verify_stand.py <project root>

Its parts must face outward, its lower parts must fit the collision box `reefhall_map.lectern` keeps (its post: 16 x 10), it must stay in the old stand's space, and every texture the
vmat names must exist. As installed: all three stands must be in the scene with no collider, with their old faces gone from the room models and their collision boxes kept, and nothing
else's collision inside the space. Seeing it in s&box is `in_game_shots.py` and `match_check.cs.txt`.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/maps/reefhall/info_stand_v2")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
failures, report = [], {}
for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"info_stand_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
    if lo[0] < -15.1 or hi[0] > 15.1 or lo[1] < -9.15 or hi[1] > 9.1 or lo[2] < -0.05 or hi[2] > 44.9:
        failures.append(f"lod{lod} is outside the old stand's space: {lo.round(2).tolist()} to {hi.round(2).tolist()}")
    # Between the floor plate and the head, only the column: it must be inside the post's box.
    body = v[(v[:, 2] > 1.0) & (v[:, 2] < 30.0)]
    if len(body) and (np.abs(body[:, 0]).max() > 8.05 or np.abs(body[:, 1]).max() > 5.5):
        failures.append(f"lod{lod}'s column leaves the collision box: x {np.abs(body[:, 0]).max():.2f}, y {np.abs(body[:, 1]).max():.2f}")
out = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "info_stand_lod0.obj"), "info_stand"], capture_output=True, text=True)
report["outward"] = out.stdout.splitlines()[0] if out.stdout else out.stderr
if out.returncode:
    failures.append(report["outward"])
vmat = open(os.path.join(NEW, "info_stand.vmat"), encoding="utf-8").read()
for rel in re.findall(r'"([^"]+\.png)"', vmat):
    if not os.path.exists(os.path.join(ASSETS, rel)):
        failures.append(f"missing {rel}")
report["compiled_files"] = sorted(f for f in os.listdir(NEW) if f.endswith("_c"))

# As installed. The map's code says where the stands are.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import reefhall_map as M  # noqa: E402

K = M.K
rooms, _ = M.build_rooms()
stands = [(name, prop) for name, model, _ in rooms for prop in model.props if prop.get("kind") == "Stand"]
report["stands"] = [(name, np.round(prop["position"], 1).tolist()) for name, prop in stands]
if len(stands) != 3:
    failures.append(f"{len(stands)} stands, not 3")
models_dir = os.path.join(ASSETS, "models/maps/reefhall")
for room in sorted({name for name, _ in stands}):
    verts, faces, material = [], [], None
    for line in open(os.path.join(models_dir, f"reefhall_{room}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            verts.append(line[2:].split()[:3])
        elif line.startswith("usemtl"):
            material = line.split()[1]
        elif line.startswith("f "):
            faces.append((material, [int(t.split("/")[0]) - 1 for t in line.split()[1:]]))
    verts = np.array(verts, float)
    # OBJ (a, b, c) is engine (c, a, b), and plan (e, n, z) is engine (n, -e, z).
    east, north, up = -verts[:, 0], verts[:, 2], verts[:, 1]
    if any(m == "rh_screen_map" for m, _ in faces):
        failures.append(f"{room}: the old screen is still drawn")
    text = open(os.path.join(models_dir, f"reefhall_{room}.vmdl"), encoding="utf-8").read()
    boxes = set()
    for block in re.findall(r'_class = "PhysicsShapeBox".*?dimensions = \[[^\]]*\]', text, re.S):
        origin = [float(x) for x in re.search(r"origin = \[([^\]]*)\]", block).group(1).split(",")]
        dims = [float(x) for x in re.search(r"dimensions = \[([^\]]*)\]", block).group(1).split(",")]
        boxes.add((round(origin[0], 1), round(origin[1], 1), round(origin[2], 1), *dims))
    for name, prop in stands:
        if name != room:
            continue
        c, d = np.asarray(prop["position"], float), np.asarray(prop["along"], float)
        u = (east - c[0]) * d[0] + (north - c[1]) * d[1]
        w = -(east - c[0]) * d[1] + (north - c[1]) * d[0]
        z = up - c[2]
        inside = (np.abs(u) <= 15.1) & (w >= -9.1) & (w <= 9.1) & (z >= -0.1) & (z <= 44.2)
        left = sum(1 for _, f in faces if inside[f].all())
        if left:
            failures.append(f"{room}: {left} faces left in the stand at {prop['position']}")
        at = K.to_world((c[0], c[1], c[2] + 17.0))
        if (round(float(at[0]), 1), round(float(at[1]), 1), round(float(at[2]), 1), 16.0, 10.0, 34.0) not in boxes:
            failures.append(f"{room}: no post collision box at {at}")

scene = json.loads(open(M.SCENE_FILE, encoding="utf-8").read())


def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))


placed = [o for o in walk(scene["GameObjects"]) if any(M.STAND_MODEL in str(c.get("Model")) for c in o.get("Components", []))]
report["placed"] = [o["Name"] for o in placed]
expected = {K.vec(K.to_world(prop["position"])) for _, prop in stands}
if {o["Position"] for o in placed} != expected or len(placed) != 3:
    failures.append(f"scene stands differ: {sorted(o['Position'] for o in placed)} against {sorted(expected)}")
if any(c["__type"] != "Sandbox.ModelRenderer" for o in placed for c in o["Components"]):
    failures.append("a placed stand has a component other than its renderer")
report["failures"] = failures
print(json.dumps(report))
sys.exit(1 if failures else 0)
