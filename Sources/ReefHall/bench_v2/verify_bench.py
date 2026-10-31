"""Check the bench from its files: python verify_bench.py <project root>

Its parts must face outward, it must fit the boxes `reefhall_map.bench` gives it (96 x 18 x 18), and every texture the vmat names must exist. As installed:
all eight benches must be in the scene with no collider, with their old faces gone from the room models, their collision boxes kept, and no other collision
inside them. Seeing it in s&box is `check_config.py` and `capture_installed.cs.txt`.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/maps/reefhall/bench_v2")
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
    if abs(lo[0]) > 48.1 or hi[0] > 48.1 or abs(lo[1]) > 9.1 or hi[1] > 9.1 or lo[2] < -0.05 or hi[2] > 18.1:
        failures.append(f"lod{lod} is outside the old bench's boxes: {lo.round(2).tolist()} to {hi.round(2).tolist()}")
out = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "bench_lod0.obj"), "bench"], capture_output=True, text=True)
report["outward"] = out.stdout.splitlines()[0] if out.stdout else out.stderr
if out.returncode:
    failures.append(report["outward"])
vmat = open(os.path.join(NEW, "bench.vmat"), encoding="utf-8").read()
for rel in re.findall(r'"([^"]+\.png)"', vmat):
    if not os.path.exists(os.path.join(ASSETS, rel)):
        failures.append(f"missing {rel}")
report["compiled_files"] = sorted(f for f in os.listdir(NEW) if f.endswith("_c"))

# As installed. The map's code says where the benches are.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import reefhall_map as M  # noqa: E402

K = M.K
rooms, _ = M.build_rooms()
benches = [(name, prop) for name, model, _ in rooms for prop in model.props if "model" in prop]
report["benches"] = len(benches)
if len(benches) != 8:
    failures.append(f"{len(benches)} benches, not 8")


def in_bench(prop, east, north, up, margin=0.1):
    """Which of these plan points lie inside the bench's 96 x 18 x 18 box."""
    c, d = np.asarray(prop["position"], float), np.asarray(prop["along"], float)
    u = (east - c[0]) * d[0] + (north - c[1]) * d[1]
    w = -(east - c[0]) * d[1] + (north - c[1]) * d[0]
    return (np.abs(u) <= 48 + margin) & (np.abs(w) <= 9 + margin) & (up >= c[2] - margin) & (up <= c[2] + 18 + margin)


# No old faces left in the room models: a face wholly inside a bench's box would be one.
models_dir = os.path.join(ASSETS, "models/maps/reefhall")
for room in ("rotunda", "galleries", "lobby", "tunnel"):
    verts, faces = [], []
    for line in open(os.path.join(models_dir, f"reefhall_{room}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            verts.append(line[2:].split()[:3])
        elif line.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    verts = np.array(verts, float)
    # OBJ (a, b, c) is engine (c, a, b), and plan (e, n, z) is engine (n, -e, z).
    east, north, up = -verts[:, 0], verts[:, 2], verts[:, 1]
    for name, prop in benches:
        if name != room:
            continue
        inside = in_bench(prop, east, north, up)
        left = sum(1 for f in faces if inside[f].all())
        if left:
            failures.append(f"{room}: {left} old faces left in the bench at {prop['position']}")
    # Each bench keeps its seat and two legs in the vmdl's collision boxes.
    text = open(os.path.join(models_dir, f"reefhall_{room}.vmdl"), encoding="utf-8").read()
    boxes = set()
    for block in re.findall(r'_class = "PhysicsShapeBox".*?dimensions = \[[^\]]*\]', text, re.S):
        origin = [float(x) for x in re.search(r"origin = \[([^\]]*)\]", block).group(1).split(",")]
        dims = [float(x) for x in re.search(r"dimensions = \[([^\]]*)\]", block).group(1).split(",")]
        boxes.add((round(origin[0], 1), round(origin[1], 1), round(origin[2], 1), *dims))
    for name, prop in benches:
        if name != room:
            continue
        c, d = np.asarray(prop["position"], float), np.asarray(prop["along"], float)
        for u, z, dims in ((0, 16.5, (96.0, 18.0, 3.0)), (-40, 7.5, (4.0, 16.0, 15.0)), (40, 7.5, (4.0, 16.0, 15.0))):
            at = K.to_world((c[0] + d[0] * u, c[1] + d[1] * u, c[2] + z))
            if (round(float(at[0]), 1), round(float(at[1]), 1), round(float(at[2]), 1), *dims) not in boxes:
                failures.append(f"{room}: no collision box {dims} at {at}")


# Nothing else in the map's collision enters a bench's box.
def own(prop, centre, size):
    return bool(in_bench(prop, *np.asarray(centre, float).reshape(3, 1))[0]) and max(size) <= 96.01


for name, prop in benches:
    for _, model, _ in rooms:
        for centre, axes, size, _ in model.boxes:
            half = np.asarray(size, float) / 2
            corners = np.array([np.asarray(centre, float) + np.asarray(axes, float).T @ (half * s) for s in np.array(np.meshgrid((-1, 1), (-1, 1), (-1, 1))).T.reshape(-1, 3)])
            if in_bench(prop, corners[:, 0], corners[:, 1], corners[:, 2], margin=0.02).all():
                continue
            c, d = np.asarray(prop["position"], float), np.asarray(prop["along"], float)
            u = (corners[:, 0] - c[0]) * d[0] + (corners[:, 1] - c[1]) * d[1]
            w = -(corners[:, 0] - c[0]) * d[1] + (corners[:, 1] - c[1]) * d[0]
            z = corners[:, 2] - c[2]
            if u.min() < 48 and u.max() > -48 and w.min() < 9 and w.max() > -9 and z.min() < 18 and z.max() > 0.5:
                failures.append(f"bench at {np.round(c, 1).tolist()} overlaps a collision box at {np.round(centre, 1).tolist()} size {np.round(size, 1).tolist()}")

# The scene places the model, with no collider, as the map's code says.
scene = json.loads(open(M.SCENE_FILE, encoding="utf-8").read())


def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))


placed = [o for o in walk(scene["GameObjects"]) if any(M.BENCH_MODEL in str(c.get("Model")) for c in o.get("Components", []))]
report["placed"] = len(placed)
expected = {K.vec(K.to_world(prop["position"])) for _, prop in benches}
if {o["Position"] for o in placed} != expected or len(placed) != 8:
    failures.append(f"scene benches differ: {sorted(o['Position'] for o in placed)} against {sorted(expected)}")
if any(c["__type"] != "Sandbox.ModelRenderer" for o in placed for c in o["Components"]):
    failures.append("a placed bench has a component other than its renderer")
report["failures"] = failures
print(json.dumps(report))
sys.exit(1 if failures else 0)
