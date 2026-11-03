"""Put the new pallets into Spillway: python install_pallets.py <project root> [--apply]. Without --apply it only reports.

The map's script isn't rerun: it rewrites far more than the pallet, and the live files carry later native work (as for the control desks).
This takes the old slabs' faces (the only rv_desk faces in it) from the live spillway_cargo.obj, and adds four pallet models to the scene
where the slabs were, each with its own collision box: two singles and a stack of two, a few degrees off square. The slabs had no collision,
so there's none to take out of the vmdl. Each step counts what it finds first and stops if a file isn't as expected, so a rerun or a
surprise changes nothing. Copies of the files go to output/asset-improvement-20261030/spillway-cargo/retired/.
"""
import json
import math
import os
import shutil
import sys
import time
import uuid

ROOT = sys.argv[1]
APPLY = "--apply" in sys.argv
MODEL = "models/maps/spillway/pallet_v2/pallet.vmdl"
OBJ = os.path.join(ROOT, "Assets/models/maps/spillway/spillway_cargo.obj")
SCENE = os.path.join(ROOT, "Assets/scenes/maps/spillway/spillway.scene")
RETIRED = os.path.join(ROOT, "output/asset-improvement-20261030/spillway-cargo/retired")
HEIGHT = 4.75
# Plan (e, n, z) and engine yaw, as compare2.py's LAYOUT about the slabs' middle (e -197, n -688). Plan (e, n, z) is engine (n, -e, z).
PALLETS = [((-258, -688, 0), 92.0), ((-198, -690, 0), 269.0), ((-197, -689, HEIGHT), 94.5), ((-139, -686, 0), 276.0)]
fails = []

# The faces. Every rv_desk face in this model belongs to the slabs: seven boxes, 84 triangles.
lines = open(OBJ, encoding="utf-8", newline="").read().split("\n")
verts, kept, cut = [], [], []
current = None
for line in lines:
    if line.startswith("v "):
        verts.append([float(x) for x in line.split()[1:4]])
    elif line.startswith("usemtl"):
        current = line.split()[1]
        if current == "rv_desk":
            continue
    elif line.startswith("f ") and current == "rv_desk":
        cut.append(line)
        continue
    kept.append(line)
if len(cut) != 84:
    fails.append(f"rv_desk: {len(cut)} triangles, expected 84")
for line in cut:
    for token in line.split()[1:]:
        x, z, n = verts[int(token.split("/")[0]) - 1]  # This OBJ is (-e, z, n).
        if not (109 <= x <= 285 and 2 <= z <= 7 and -712 <= n <= -663):
            fails.append(f"rv_desk has a vertex away from the slabs: {x}, {z}, {n}")
            break
print("faces to cut:", len(cut))

# The scene. Each pallet is a copy of a control desk's object, so it has every field the editor saves.
raw = open(SCENE, encoding="utf-8", newline="").read()
data = json.loads(raw)
if json.dumps(data, indent=2, ensure_ascii=False) + "\n" != raw:
    fails.append("the scene doesn't round-trip byte for byte, so rewriting it would change more than the pallets")
root = next(g for g in data["GameObjects"] if g.get("Name") == "Spillway")
desk = next(c for c in root["Children"] if c["Name"] == "Control Desk 1")
if MODEL in raw:
    fails.append("the scene already has the new pallets")
meta = json.load(open(os.path.join(ROOT, "Assets", MODEL + ".meta"), encoding="utf-8"))
guid = lambda key: str(uuid.uuid5(uuid.NAMESPACE_URL, "hc1/spillway/yard-pallet/" + key))
for k, ((e, n, z), yaw) in enumerate(PALLETS, 1):
    pallet = json.loads(json.dumps(desk))
    pallet["__guid"] = guid(f"{k}")
    pallet["Name"] = f"Yard Pallet {k}"
    pallet["Position"] = f"{n:g},{-e:g},{z:g}"
    half = math.radians(yaw) / 2
    pallet["Rotation"] = f"0,0,{math.sin(half):.7f},{math.cos(half):.7f}"
    types = [c["__type"] for c in pallet["Components"]]
    if types != ["Sandbox.ModelRenderer", "Sandbox.ModelCollider"]:
        fails.append(f"Control Desk 1's components: {types}")
    for component in pallet["Components"]:
        component["__guid"] = guid(f"{k}/{component['__type']}")
        component["Model"] = {"Id": meta["guid"], "Path": MODEL}
    root["Children"].append(pallet)
    print("pallet", k, "at", pallet["Position"], "yaw", yaw)


# Nothing that spawns or stands should be on the pallets' ground.
def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))


for item in walk(data["GameObjects"]):
    if item.get("Name", "").startswith("Yard Pallet") or "," not in item.get("Position", ""):
        continue
    x, y, z = [float(v) for v in item["Position"].split(",")]
    if -715 <= x <= -660 and 100 <= y <= 290 and -5 <= z <= 30:
        print("  near the pallets:", item.get("Name"), item["Position"])

if fails:
    print("STOPPED, nothing written:")
    for f in fails:
        print(" ", f)
    sys.exit(1)
if not APPLY:
    print("dry run: nothing written")
    sys.exit(0)
os.makedirs(RETIRED, exist_ok=True)
for path in (OBJ, SCENE):
    shutil.copy2(path, os.path.join(RETIRED, os.path.basename(path)))


def write(path, text):
    # Written beside the file and moved over it, so a failure can't leave it half written. The open editor can hold a file it's
    # compiling, which makes the move fail with access denied for a moment, so it tries again.
    incoming = path + ".pallet-incoming"
    with open(incoming, "w", encoding="utf-8", newline="") as h:
        h.write(text)
    for attempt in range(40):
        try:
            os.replace(incoming, path)
            return
        except PermissionError:
            time.sleep(0.5)
    raise SystemExit(f"couldn't replace {path}; the new text is in {incoming}")


write(OBJ, "\n".join(kept))
write(SCENE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("installed")
