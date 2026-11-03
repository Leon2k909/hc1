"""Put the new canvas cover into Spillway: python install_canvas.py <project root> [--apply]. Without --apply it only reports.

The map's script isn't rerun (as for the control desks and the yard pallets). This takes the old cover's faces (every sw_tarp face) and its two
strap boxes (the rv_dark faces inside their bounds) from the live spillway_east.obj, and adds the model to the scene with no collider: the
old cover's collision box is in the east model's hulls, which aren't touched, and the load fills it. Each step counts what it finds first
and stops if a file isn't as expected, so a rerun or a surprise changes nothing. Copies of the files go to
output/asset-improvement-20261030/spillway-canvas/retired/.
"""
import json
import os
import shutil
import sys
import time
import uuid

ROOT = sys.argv[1]
APPLY = "--apply" in sys.argv
MODEL = "models/maps/spillway/canvas_cover_v2/canvas_cover.vmdl"
OBJ = os.path.join(ROOT, "Assets/models/maps/spillway/spillway_east.obj")
SCENE = os.path.join(ROOT, "Assets/scenes/maps/spillway/spillway.scene")
RETIRED = os.path.join(ROOT, "output/asset-improvement-20261030/spillway-canvas/retired")
# Engine position: plan (e 1550, n -1705) on the B2 deck at z 128. Its X is the map's n and its Y the map's -e, so no turn.
POSITION, ROTATION = "-1705,-1550,128", "0,0,0,1"
fails = []

lines = open(OBJ, encoding="utf-8", newline="").read().split("\n")
verts, kept, tarp, straps = [], [], [], []
current = None


def inside(line, e0, e1, z0, z1, n0, n1):
    for token in line.split()[1:]:
        x, z, n = verts[int(token.split("/")[0]) - 1]  # This OBJ is (-e, z, n).
        if not (-e1 <= x <= -e0 and z0 <= z <= z1 and n0 <= n <= n1):
            return False
    return True


for line in lines:
    if line.startswith("v "):
        verts.append([float(x) for x in line.split()[1:4]])
    elif line.startswith("usemtl"):
        current = line.split()[1]
        if current == "sw_tarp":
            continue
    elif line.startswith("f ") and current == "sw_tarp":
        tarp.append(line)
        continue
    elif line.startswith("f ") and current == "rv_dark" and inside(line, 1497, 1603, 127.9, 220.1, -1772.1, -1638.9):
        straps.append(line)
        continue
    kept.append(line)
if len(tarp) != 11520:
    fails.append(f"sw_tarp: {len(tarp)} triangles, expected 11520")
if len(straps) != 48:
    fails.append(f"strap faces: {len(straps)} triangles, expected 48")
if any(not inside(line, 1479, 1621, 127.9, 220.3, -1771, -1639) for line in tarp):
    fails.append("sw_tarp has a face away from the cover")
print("faces to cut:", len(tarp), "cover,", len(straps), "straps")

raw = open(SCENE, encoding="utf-8", newline="").read()
data = json.loads(raw)
if json.dumps(data, indent=2, ensure_ascii=False) + "\n" != raw:
    fails.append("the scene doesn't round-trip byte for byte, so rewriting it would change more than the cover")
root = next(g for g in data["GameObjects"] if g.get("Name") == "Spillway")
template = next(c for c in root["Children"] if c["Name"] == "Yard Pallet 1")
if MODEL in raw:
    fails.append("the scene already has the new cover")
meta = json.load(open(os.path.join(ROOT, "Assets", MODEL + ".meta"), encoding="utf-8"))
guid = lambda key: str(uuid.uuid5(uuid.NAMESPACE_URL, "hc1/spillway/canvas-cover/" + key))
cover = json.loads(json.dumps(template))
cover["__guid"] = guid("object")
cover["Name"] = "B2 Canvas Cover"
cover["Position"] = POSITION
cover["Rotation"] = ROTATION
types = [c["__type"] for c in cover["Components"]]
if types != ["Sandbox.ModelRenderer", "Sandbox.ModelCollider"]:
    fails.append(f"Yard Pallet 1's components: {types}")
# Drawn only: the east model's hull is its collision.
cover["Components"] = [c for c in cover["Components"] if c["__type"] == "Sandbox.ModelRenderer"]
for component in cover["Components"]:
    component["__guid"] = guid(component["__type"])
    component["Model"] = {"Id": meta["guid"], "Path": MODEL}
root["Children"].append(cover)
print("cover at", POSITION)


def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))


# Nothing that spawns or stands should be under the skirt (x +-87, y +-92 about the cover's middle).
for item in walk(data["GameObjects"]):
    if item.get("Name") == "B2 Canvas Cover" or "," not in item.get("Position", ""):
        continue
    x, y, z = [float(v) for v in item["Position"].split(",")]
    if abs(x + 1705) <= 95 and abs(y + 1550) <= 100 and 120 <= z <= 240:
        print("  near the cover:", item.get("Name"), item["Position"])

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
    incoming = path + ".canvas-incoming"
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
