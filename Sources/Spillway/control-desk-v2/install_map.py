"""Put the new control desks into Spillway: python install_map.py <project root> [--apply]. Without --apply it only reports.

The map's script isn't rerun: it rewrites far more than the desks, and the live files carry later native work. This takes the old desks'
faces from the live spillway_control.obj and their four collision boxes from its vmdl, and adds the four models to the scene with their
own collision. Each step counts what it finds first and stops if the file isn't as expected, so a rerun or a surprise changes nothing.
Copies of the three files go to output/asset-improvement-20261030/spillway-desk/retired/.
"""
import json
import os
import re
import shutil
import sys
import uuid

ROOT = sys.argv[1]
APPLY = "--apply" in sys.argv
DESKS = (-190, 60, 310, 500)  # Plan e. Plan (e, n, z) is engine (n, -e, z).
MODEL = "models/props/spillway/control_desk_v2/control_desk.vmdl"
OBJ = os.path.join(ROOT, "Assets/models/maps/spillway/spillway_control.obj")
VMDL = os.path.join(ROOT, "Assets/models/maps/spillway/spillway_control.vmdl")
SCENE = os.path.join(ROOT, "Assets/scenes/maps/spillway/spillway.scene")
RETIRED = os.path.join(ROOT, "output/asset-improvement-20261030/spillway-desk/retired")
fails = []

# The faces. Every rv_desk and rv_screens face in this model belongs to the four desks.
lines = open(OBJ, encoding="utf-8", newline="").read().split("\n")
verts, kept, cut = [], [], {"rv_desk": [], "rv_screens": []}
current = None
for line in lines:
    if line.startswith("v "):
        verts.append([float(x) for x in line.split()[1:4]])
    elif line.startswith("usemtl"):
        current = line.split()[1]
        if current in cut:
            continue
    elif line.startswith("f ") and current in cut:
        cut[current].append(line)
        continue
    kept.append(line)
for name, want in (("rv_desk", 48), ("rv_screens", 8)):
    if len(cut[name]) != want:
        fails.append(f"{name}: {len(cut[name])} triangles, expected {want}")
for name, faces in cut.items():
    for line in faces:
        for token in line.split()[1:]:
            x, z, n = verts[int(token.split("/")[0]) - 1]  # OBJ is engine (Y, Z, X).
            if not (1236 <= n <= 1311 and 236 <= z <= 324 and min(abs(x + e) for e in DESKS) <= 61):
                fails.append(f"{name} has a vertex away from the desks: {x}, {z}, {n}")
                break
print("faces to cut:", {k: len(v) for k, v in cut.items()})

# The collision boxes.
vmdl = open(VMDL, encoding="utf-8", newline="").read()
new_vmdl = vmdl
for e in DESKS:
    pattern = re.compile(r'[ \t]*\{\s*_class = "PhysicsShapeBox"\s*parent_bone = ""\s*surface_prop = "metal"\s*collision_tags = "solid"\s*origin = \[ 1275\.0000, ' + f"{-float(e):.4f}" + r', 253\.0000 \]\s*angles = \[ [^\]]*\]\s*dimensions = \[ 120\.0000, 70\.0000, 34\.0000 \]\s*\},?[ \t]*\r?\n')
    new_vmdl, count = pattern.subn("", new_vmdl)
    if count != 1:
        fails.append(f"collision box at e {e}: found {count}")
print("collision boxes to cut:", len(DESKS) if len(new_vmdl) < len(vmdl) else 0)

# The scene. Each desk is a copy of the Control object's shape, so it has every field the editor saves.
raw = open(SCENE, encoding="utf-8", newline="").read()
data = json.loads(raw)
if json.dumps(data, indent=2, ensure_ascii=False) + "\n" != raw:
    fails.append("the scene doesn't round-trip byte for byte, so rewriting it would change more than the desks")
root = next(g for g in data["GameObjects"] if g.get("Name") == "Spillway")
control = next(c for c in root["Children"] if c["Name"] == "Control")
if MODEL in raw:
    fails.append("the scene already has the new desks")
meta = json.load(open(os.path.join(ROOT, "Assets", MODEL + ".meta"), encoding="utf-8"))
guid = lambda key: str(uuid.uuid5(uuid.NAMESPACE_URL, "hc1/spillway/control-desk/" + key))
for k, e in enumerate(DESKS, 1):
    desk = json.loads(json.dumps(control))
    desk["__guid"] = guid(f"{k}")
    desk["Name"] = f"Control Desk {k}"
    desk["Position"] = f"1275,{-e},236"
    desk["Rotation"] = "0,0,1,0"  # Yaw 180: the operator's side, the model's +X, faces into the room.
    types = [c["__type"] for c in desk["Components"]]
    if types != ["Sandbox.ModelRenderer", "Sandbox.ModelCollider"]:
        fails.append(f"Control's components: {types}")
    for component in desk["Components"]:
        component["__guid"] = guid(f"{k}/{component['__type']}")
        component["Model"] = {"Id": meta["guid"], "Path": MODEL}
    root["Children"].append(desk)
    print("desk", k, "at", desk["Position"])

# Nothing that spawns or stands should be inside or on the desks' volume.
def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))


for item in walk(data["GameObjects"]):
    if item.get("Name", "").startswith("Control Desk") or "," not in item.get("Position", ""):
        continue
    x, y, z = [float(v) for v in item["Position"].split(",")]
    if 1236 <= x <= 1314 and 232 <= z <= 325 and min(abs(y + e) for e in DESKS) <= 64:
        print("  near a desk:", item.get("Name"), item["Position"])

if fails:
    print("STOPPED, nothing written:")
    for f in fails:
        print(" ", f)
    sys.exit(1)
if not APPLY:
    print("dry run: nothing written")
    sys.exit(0)
os.makedirs(RETIRED, exist_ok=True)
for path in (OBJ, VMDL, SCENE):
    shutil.copy2(path, os.path.join(RETIRED, os.path.basename(path)))


def write(path, text):
    # Written beside the file and moved over it, so a failure can't leave it half written.
    incoming = path + ".desk-incoming"
    with open(incoming, "w", encoding="utf-8", newline="") as h:
        h.write(text)
    os.replace(incoming, path)


write(OBJ, "\n".join(kept))
write(VMDL, new_vmdl)
write(SCENE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("installed")
