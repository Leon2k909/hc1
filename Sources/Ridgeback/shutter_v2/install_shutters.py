"""Install the shutters: python install_shutters.py <project root> [--write]

Cuts the old leaves' faces from town_house.obj, adds a "Shutters" group to the town house prefab, renderers only (the old leaves had no collision), and gives each new
object and component its fixed id in ridgeback.scene's instance, as ridgeback_buildings --place would, since an object in a prefab needs one. It re-reads the prefab and scene,
so what other sessions have changed there stays. Each new leaf must fit an old leaf exactly, and all 34 must pair up, or nothing is written. Without --write it only reports.
Files are moved into place with os.replace, and the originals are kept in the work folder's before-install.
"""
import json
import math
import os
import shutil
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import ridgeback_buildings as RB  # noqa: E402

NAME = "town_house"
OBJ = os.path.join(ROOT, "Assets/models/buildings/town_house/town_house.obj")
PREFAB = os.path.join(ROOT, "Assets/prefabs/buildings/town_house.prefab")
SCENE = os.path.join(ROOT, "Assets/scenes/maps/Ridgeback/ridgeback.scene")
BACKUP = os.path.join(ROOT, "output/asset-improvement-20261030/shutter/before-install")
LEAF = (1.5, 25.0, 64.0)

model = RB.town_house()
places = model.shutters
print("the map script hangs", len(places), "leaves:", sum(p["side"] == "l" for p in places), "l,", sum(p["side"] == "r" for p in places), "r", flush=True)
if len(places) != 34:
    sys.exit("Expected 34 leaves. Nothing written.")

# The old leaves, from what the model draws.
with open(OBJ, encoding="utf-8", newline="") as h:
    lines = h.readlines()
v = []
for line in lines:
    if line.startswith("v "):
        a, b, c = line[2:].split()[:3]
        v.append((float(c), float(a), float(b)))  # OBJ (a, b, c) is engine (c, a, b).
v = np.array(v)
current = None
drop = []
for n, line in enumerate(lines):
    if line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current == "shutter_green":
        drop.append(n)
triangles = [[int(t.split("/")[0]) - 1 for t in lines[n].split()[1:]] for n in drop]
if sum(len(t) - 2 for t in triangles) != 408:
    sys.exit("Expected the old leaves' 408 triangles. Nothing written.")
old = []
for k in range(0, len(triangles), 12):
    pts = v[np.array(triangles[k : k + 12]).ravel()]
    old.append((pts.min(0), pts.max(0)))
if len(old) != 34:
    sys.exit("Expected 34 old leaves. Nothing written.")

# Each new leaf must land exactly on one old leaf, and on a different one.
matched = set()
for place in places:
    yaw = math.radians(place["yaw"])
    out, own_y = np.array((math.cos(yaw), math.sin(yaw), 0.0)), np.array((-math.sin(yaw), math.cos(yaw), 0.0))
    at = np.array(place["position"])
    corners = np.array([at + out * x + own_y * y + np.array((0, 0, z)) for x in (0.0, LEAF[0]) for y in (-LEAF[1] / 2, LEAF[1] / 2) for z in (0.0, LEAF[2])])
    lo, hi = corners.min(0), corners.max(0)
    hit = [i for i, (a, b) in enumerate(old) if np.abs(a - lo).max() < 0.02 and np.abs(b - hi).max() < 0.02]
    if len(hit) != 1 or hit[0] in matched:
        sys.exit(f"A new leaf doesn't fit one old leaf: {place}, {lo}, {hi}. Nothing written.")
    matched.add(hit[0])
print("every new leaf fits one old leaf:", len(matched), flush=True)
# And each hinge must be towards its window: its partner stands exactly one window's width away on the hinge side, hinged back towards it. (The nearest leaf can be the next
# window's, so that won't do.) A leaf's middle is half a leaf from its hinge, and the windows' surrounds are 52 in across.
ACROSS = LEAF[1] + 52.0
for place in places:
    yaw = math.radians(place["yaw"])
    own_y = np.array((-math.sin(yaw), math.cos(yaw), 0.0))
    at = np.array(place["position"])
    hinge = own_y if place["side"] == "l" else -own_y
    partner = [q for q in places if np.abs(np.array(q["position"]) - (at + hinge * ACROSS)).max() < 0.1]
    if len(partner) != 1 or partner[0]["side"] == place["side"]:
        sys.exit(f"A leaf's hinge isn't towards its window: {place}. Nothing written.")
print("every hinge faces its window, its partner across it", flush=True)

# The model without its leaves.
gone = set(drop)
kept = [line for n, line in enumerate(lines) if n not in gone]
final = []
for n, line in enumerate(kept):
    if line.startswith("usemtl"):
        following = next((x for x in kept[n + 1 :] if x.startswith(("f ", "usemtl"))), "")
        if not following.startswith("f "):
            print("no faces left under", line.strip())
            continue
    final.append(line)

# The prefab, as it is now, with the group added.
prefab_text = open(PREFAB, "rb").read().decode("utf-8")
prefab = json.loads(prefab_text)
root = prefab["RootObject"]
group = RB.prefab_object(f"{NAME}/shutters", "Shutters", children=[RB.shutter_object(NAME, k, place) for k, place in enumerate(places)])
root["Children"] = [c for c in root["Children"] if c.get("Name") != "Shutters"] + [group]
newline = "\r\n" if "\r\n" in prefab_text else "\n"
new_prefab = json.dumps(prefab, indent=2, ensure_ascii=False).replace("\n", newline) + (newline if prefab_text.endswith("\n") else "")
doors = [c for c in root["Children"] if c.get("Name") == "Doors"][0]["Children"]
print("doors now draw:", sorted({d["Components"][0]["Model"] for d in doors}), flush=True)

# The scene's instance: fixed ids for the new objects and components.
scene_text = open(SCENE, "rb").read().decode("utf-8")
scene_newline = "\r\n" if "\r\n" in scene_text else "\n"
scene = json.loads(scene_text)


def instances(nodes):
    for node in nodes:
        if isinstance(node.get("__Prefab"), dict) and node["__Prefab"].get("Path") == f"prefabs/buildings/{NAME}.prefab":
            yield node
        yield from instances(node.get("Children", []))


found = list(instances(scene["GameObjects"]))
if len(found) != 1:
    sys.exit(f"Expected one town house in ridgeback.scene, found {len(found)}. Nothing written.")
ids = []


def collect(node):
    ids.append(node["__guid"])
    ids.extend(c["__guid"] for c in node.get("Components", []))
    for child in node.get("Children", []):
        collect(child)


collect(group)
mapping = found[0]["__PrefabIdToInstanceId"]
added = 0
for pid in ids:
    if pid not in mapping:
        mapping[pid] = RB.gid(f"scene/{NAME}/{pid}")
        added += 1
found[0]["__PrefabIdToInstanceId"] = dict(sorted(mapping.items()))
new_scene = json.dumps(scene, indent=2, ensure_ascii=False).replace("\n", scene_newline) + (scene_newline if scene_text.endswith("\n") else "")
print("ids added to the scene's instance:", added, "of", len(ids), "; prefab grows by", len(new_prefab) - len(prefab_text), "bytes; scene by", len(new_scene) - len(scene_text), flush=True)
if not WRITE:
    print("report only: pass --write to change the files")
    sys.exit(0)
os.makedirs(BACKUP, exist_ok=True)
for path in (OBJ, PREFAB, SCENE):
    backup = os.path.join(BACKUP, os.path.basename(path))
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
temporary = OBJ + ".installing"
with open(temporary, "w", encoding="utf-8", newline="") as h:
    h.writelines(final)
os.replace(temporary, OBJ)
for path, body in ((PREFAB, new_prefab), (SCENE, new_scene)):
    temporary = path + ".installing"
    with open(temporary, "wb") as h:
        h.write(body.encode("utf-8"))
    os.replace(temporary, path)
print("written", flush=True)
