"""Check the shutters from their files: python verify_shutter.py <project root> <export dir>

Both leaves' parts must face outward, they must fit the old leaf, be mirror images, carry no physics and have their textures, and the old
town house must be unchanged. Compiling and seeing them in s&box is not covered.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, EXPORT = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(EXPORT, "models/props/ridgeback/shutter_v2")
MATS = "materials/ridgeback/shutter_v2"
OLD_OBJ = "models/buildings/town_house/town_house.obj"
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
    return np.array(v, float)[:, [2, 0, 1]], f  # OBJ (a, b, c) is engine (c, a, b).


# The old leaf: 25 wide, 64 high, 1.5 thick, in every one of its 34 placements.
sizes = {}
faces = 0
current = None
vertices = []
triangles = []
for line in open(os.path.join(ASSETS, OLD_OBJ), encoding="utf-8"):
    if line.startswith("v "):
        vertices.append(line[2:].split())
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current == "shutter_green":
        triangles.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
v = np.array(vertices, float)
for k in range(0, len(triangles), 12):
    s = tuple(sorted(np.ptp(v[np.array(triangles[k : k + 12]).ravel()], axis=0).round(1).tolist()))
    sizes[s] = sizes.get(s, 0) + 1
report["old_leaves"] = {str(k): n for k, n in sizes.items()}
check(sizes == {(1.5, 25.0, 64.0): 34}, f"expected 34 old leaves of 1.5 x 25 x 64: {sizes}")
changed = subprocess.run(["git", "status", "--porcelain", "--", f"Assets/{OLD_OBJ}"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
check(changed == "", f"the old town house model changed: {changed}")

for side, sign in (("l", 1), ("r", -1)):
    name = f"shutter_{side}"
    report[name] = {}
    for lod in range(4):
        vs, f = read_obj(os.path.join(NEW, f"{name}_lod{lod}.obj"))
        lo, hi = vs.min(0), vs.max(0)
        report[name][f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
        if lod == 0:
            # The leaf itself fills the old box. The hinges' pintles and the dog stand off it, as real ones do.
            # The dog's foot is let 0.06 in into the wall, as it's fixed there, and nothing else goes behind the wall's face.
            check(-0.1 < lo[0] <= 0.0 and hi[0] < 2.6, f"{name}: depth off the wall is wrong: {lo} {hi}")
            check(abs(lo[2]) < 0.01 and abs(hi[2] - 64) < 0.01, f"{name}: height isn't the old 64: {lo} {hi}")
            check(lo[1] > -14.6 and hi[1] < 14.6, f"{name}: width goes too far past the old 25: {lo} {hi}")
        if lod:
            check(f < report[name][f"lod{lod - 1}"]["triangles"], f"{name} lod{lod} isn't lighter")
    outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{name}_lod0.obj"), "shutter"], capture_output=True, text=True)
    report[name]["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
    check(outward.returncode == 0, f"{name}: {report[name]['outward']}")
    vmdl = open(os.path.join(NEW, f"{name}.vmdl"), encoding="utf-8").read()
    check("PhysicsShape" not in vmdl and "PhysicsHull" not in vmdl, f"{name}: the old shutters have no physics, and this mustn't add any")
    check(f'to = "{MATS}/shutter.vmat"' in vmdl, f"{name}: vmdl doesn't remap to its material")
    for ref in re.findall(r'filename = "([^"]+)"', vmdl):
        check(os.path.exists(os.path.join(EXPORT, ref)), f"{name}: vmdl names missing {ref}")
a, _ = read_obj(os.path.join(NEW, "shutter_l_lod0.obj"))
b, _ = read_obj(os.path.join(NEW, "shutter_r_lod0.obj"))
# As sets: mirroring reverses each triangle's winding, so the vertices are written in a different order.
points = lambda p: {tuple(q) for q in np.round(p, 3).tolist()}
check(points(a * np.array((1, -1, 1))) == points(b), "the two leaves aren't mirror images")
vmat = open(os.path.join(EXPORT, MATS, "shutter.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
report["textures"] = textures
check(len(textures) == 5, "expected five textures")
for tex in textures:
    check(os.path.exists(os.path.join(EXPORT, tex)), f"missing {tex}")
report["in_assets"] = [p for p in ("models/props/ridgeback/shutter_v2", MATS) if os.path.exists(os.path.join(ASSETS, p))]
report["compiled_files"] = [f for d in (NEW, os.path.join(EXPORT, MATS)) for f in os.listdir(d) if f.endswith("_c")]
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
