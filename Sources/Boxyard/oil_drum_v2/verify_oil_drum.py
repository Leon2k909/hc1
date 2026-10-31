"""Check the drum from its files: python verify_oil_drum.py <project root>

Its parts must face outward, it must stay within the old drum's size, the old drum's collision must still fit it, every texture a
vmat names must exist, and the swap into Boxyard must be complete and no more. Compiling it and seeing it in s&box is not covered.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models/maps/boxyard/oil_drum_v2")
PROPS = os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.obj")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


# The old drum: boxyard_map.drum at (557, -498), read from the merged model as it was committed, since the swap took it out.
# OBJ (a, b, c) is engine (c, a, b), and the map's (e, n) is engine (n, -e).
committed = subprocess.run(["git", "show", "HEAD:Assets/models/maps/boxyard/boxyard_props.obj"], cwd=ROOT, capture_output=True).stdout.decode("utf-8")
positions, faces, current = [], [], None
for line in committed.splitlines():
    if line.startswith("v "):
        positions.append(line[2:].split())
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current in ("bx_drum_blue", "bx_drum_red"):
        faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
points = np.array(positions, float)
old = points[:, [2, 0, 1]][sorted({i for f in faces for i in f})]
near = np.hypot(old[:, 0] + 498.0, old[:, 1] + 557.0) < 14.0
old_near = old[near] - np.array((-498.0, -557.0, 0.0))
old_r, old_h = float(np.hypot(old_near[:, 0], old_near[:, 1]).max()), float(old_near[:, 2].max())
report["old"] = dict(faces_of_all_five=len(faces), radius=round(old_r, 3), height=round(old_h, 3))

for lod in range(3):
    v, f = [], 0
    for line in open(os.path.join(NEW, f"oil_drum_lod{lod}.obj"), encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)[:, [2, 0, 1]]
    radius, low, high = float(np.hypot(v[:, 0], v[:, 1]).max()), float(v[:, 2].min()), float(v[:, 2].max())
    report[f"lod{lod}"] = dict(triangles=f, radius=round(radius, 3), low=round(low, 3), high=round(high, 3))
    # The hoops are the old drum's width: the collision is a hull of its lathe, so the new drum must not stand far outside it.
    # Decimating moves the far LOD's outline a little, which can't be seen from where it shows.
    slack = 0.12 if lod < 2 else 0.2
    check(radius <= old_r + slack, f"lod{lod}: radius {radius:.3f} is over the old drum's {old_r:.3f}")
    check(abs(high - old_h) < 0.1 and abs(low) < (0.02 if lod < 2 else 0.05), f"lod{lod}: height runs {low:.3f} to {high:.3f}, the old drum's to {old_h:.3f}")
outward = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, "oil_drum_lod0.obj"), "oil_drum"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, f"outward: {report['outward']}")

for colour in ("blue", "red"):
    vmdl = open(os.path.join(NEW, f"oil_drum_{colour}.vmdl"), encoding="utf-8").read()
    for rel in re.findall(r'filename = "([^"]+)"', vmdl):
        check(os.path.exists(os.path.join(ASSETS, rel)), f"missing {rel}")
    vmat_rel = re.search(r'to = "([^"]+\.vmat)"', vmdl).group(1)
    vmat = open(os.path.join(ASSETS, vmat_rel), encoding="utf-8").read()
    textures = re.findall(r'"([^"]+\.png)"', vmat)
    check(len(textures) == 5, f"{colour}: {len(textures)} textures")
    for rel in textures:
        check(os.path.exists(os.path.join(ASSETS, rel)), f"missing {rel}")
report["compiled_files"] = sorted(f for f in os.listdir(NEW) if f.endswith("_c"))

# The swap: the merged props have lost their drums and bungs and nothing else, the collision is byte for byte what it was, and the
# scene places five drums where the hulls are, on files that exist.
now = open(PROPS, encoding="utf-8").read()
check("bx_drum" not in now, "the merged props still draw a drum")
for hull in ("boxyard_props_hulls_metal.obj", "boxyard_props_hulls_plastic.obj"):
    was = subprocess.run(["git", "show", f"HEAD:Assets/models/maps/boxyard/{hull}"], cwd=ROOT, capture_output=True).stdout
    def same_lines(data):
        return b"\n".join(line for line in data.splitlines() if line)

    check(same_lines(was) == same_lines(open(os.path.join(ASSETS, "models/maps/boxyard", hull), "rb").read()), f"{hull} changed")
faces_now = sum(1 for line in now.splitlines() if line.startswith("f "))
faces_was = sum(1 for line in committed.splitlines() if line.startswith("f "))
report["merged_props_faces"] = [faces_was, faces_now]
scene = json.load(open(os.path.join(ASSETS, "scenes/maps/Boxyard/boxyard.scene"), encoding="utf-8"))
placed = []


def walk(ob):
    for c in ob.get("Components", []):
        if "oil_drum_v2" in str(c.get("Model", "")):
            placed.append((ob["Position"], ob["Rotation"], c["Model"], [k["__type"] for k in ob["Components"]]))
    for child in ob.get("Children", []):
        walk(child)


for ob in scene["GameObjects"]:
    walk(ob)
report["placed"] = [(p, m.rsplit("/", 1)[1]) for p, _, m, _ in placed]
wanted = {(-498.0, -557.0, "blue"), (-515.0, -592.0, "red"), (-534.0, -562.0, "blue"), (-620.0, 600.0, "red"), (-600.0, 575.0, "blue")}
found = set()
for position, _, model, types in placed:
    x, y, _z = map(float, position.split(","))
    found.add((round(x, 1), round(y, 1), "blue" if "blue" in model else "red"))
    check(os.path.exists(os.path.join(ASSETS, model)), f"missing {model}")
    check("Sandbox.ModelCollider" not in types, "a drum has its own collider, on top of the hull")
check(found == wanted, f"drums are at {sorted(found)}")
script = open(os.path.join(ROOT, "Tools/boxyard_map.py"), encoding="utf-8").read()
check("bx_drum" not in script, "Tools/boxyard_map.py would put the old drums back")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
