"""Install the power cabinets in Sewage: python install.py <project root> [--copy]

Cuts the three old cabinets and their lamps from sewage_details.obj, adds the new model three times to sewage.scene, and moves
each cabinet's green light to the new status lamp. The hulls in sewage_details.vmdl stay, so the bodies collide as before.
Without --copy it only says what it would do. Each file is checked first, so nothing is changed if another session has moved it on.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(sys.argv[1])
COPY = "--copy" in sys.argv
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K  # noqa: E402

OBJ = ROOT / "Assets/models/maps/sewage/sewage_details.obj"
SCENE = ROOT / "Assets/scenes/maps/sewage/sewage.scene"
META = ROOT / "Assets/models/maps/sewage/power_cabinet_v2/power_cabinet.vmdl.meta"
MODEL = "models/maps/sewage/power_cabinet_v2/power_cabinet.vmdl"
IDS = K.SceneIds("d6ab2592-265b-48f5-8afe-97c5206e0c43")
# World position, yaw, old light position, new light position.
CABINETS = [
    ((470, 958, 0), -90, "421,958,98", "446,934,104.5", 37),
    ((600, -946, 0), 90, "551,-946,98", "624,-922,104.5", 38),
    ((830, 870, 352), -90, "781,870,450", "806,846,456.5", 39),
]
EXPECTED_CUT = 594


def in_cut(p):
    x, y, z = p
    for (ax, ay, az), *_ in CABINETS:
        body = abs(x - ax) <= 38.2 and abs(y - ay) <= 19.2 and az - 0.1 <= z <= az + 115.1
        # The old lamp stands off its south end, and its guard bars reach plan n - 47.
        lamp = ax - 47.6 <= x <= ax - 34.8 and abs(y - ay) <= 10.1 and az + 98.2 <= z <= az + 109.1
        if body or lamp:
            return True
    return False


def replace_file(path, text):
    """Beside the file and moved over it: the open editor can refuse a plain overwrite."""
    incoming = path.with_name(path.name + ".cabinet-incoming")
    with open(incoming, "w", encoding="utf-8", newline="") as h:
        h.write(text)
    os.replace(incoming, path)


# ---- The OBJ: drop the cut triangles. Vertices stay, as they're shared by index.
source = open(OBJ, encoding="utf-8", newline="").read()
newline = "\r\n" if "\r\n" in source else "\n"
positions = []
kept = []
cut = {}
material = None
for line in source.split(newline):
    if line.startswith("v "):
        _, a, b, c = line.split()
        # The OBJ's axes are the world's ( y, z, x ).
        positions.append((float(c), float(a), float(b)))
    elif line.startswith("usemtl "):
        material = line[7:].strip()
    elif line.startswith("f "):
        corners = [positions[int(t.split("/")[0]) - 1] for t in line.split()[1:]]
        if all(in_cut(c) for c in corners):
            cut[material] = cut.get(material, 0) + 1
            continue
    kept.append(line)
print("triangles to cut, by paint:", cut, "total", sum(cut.values()))
if sum(cut.values()) != EXPECTED_CUT:
    sys.exit(f"Expected to cut {EXPECTED_CUT}: the OBJ isn't in the state the comparison was made on.")

# ---- The scene: as text, so that nothing else in it changes.
scene_text = open(SCENE, encoding="utf-8", newline="").read()
scene_nl = "\r\n" if "\r\n" in scene_text else "\n"
original = json.loads(scene_text)
if any(item.get("Name", "").startswith("Power cabinet") for item in original["GameObjects"]):
    sys.exit("The cabinets are already in the scene.")
template = next(item for item in original["GameObjects"] if item.get("Name") == "Waterworks details")
guid = json.loads(META.read_text(encoding="utf-8"))["guid"]
blocks = []
for index, (at, yaw, *_rest) in enumerate(CABINETS):
    item = json.loads(json.dumps(template))
    key = f"power_cabinet/{index}"
    item["__guid"] = IDS(key)
    item["Name"] = f"Power cabinet {index + 1}"
    item["Position"] = ",".join(str(v) for v in at)
    item["Rotation"] = K.angles_rotation(0, yaw)
    for component, part in zip(item["Components"], ("render", "collision")):
        component["__guid"] = IDS(f"{key}/{part}")
        component["Model"] = {"Id": guid, "Path": MODEL}
    block = json.dumps(item, indent=2)
    blocks.append("\n".join("    " + line for line in block.split("\n")).replace("\n", scene_nl))
anchor = scene_text.index('"Name": "Waterworks signage"')
start = scene_text.rfind(scene_nl + "    {" + scene_nl, 0, anchor) + len(scene_nl)
updated = scene_text[:start] + ("," + scene_nl).join(blocks) + "," + scene_nl + scene_text[start:]
for _at, _yaw, old, new, number in CABINETS:
    pattern = re.compile(r'("Name": "Work light %d",\s+"Position": ")%s(")' % (number, re.escape(old)))
    updated, count = pattern.subn(lambda m: m.group(1) + new + m.group(2), updated)
    if count != 1:
        sys.exit(f"Work light {number} isn't where it was.")

# The result must differ from the original by exactly this.
result = json.loads(updated)
added = [item["Name"] for item in result["GameObjects"] if item.get("Name", "").startswith("Power cabinet")]
rest = [item for item in result["GameObjects"] if not item.get("Name", "").startswith("Power cabinet")]
compare = json.loads(json.dumps(original))
for item in compare["GameObjects"]:
    if item.get("Name") == "Practical work lights":
        for child in item["Children"]:
            for _at, _yaw, _old, new, number in CABINETS:
                if child["Name"] == f"Work light {number}":
                    child["Position"] = new
if rest != compare["GameObjects"] or {k: v for k, v in result.items() if k != "GameObjects"} != {k: v for k, v in compare.items() if k != "GameObjects"}:
    sys.exit("The scene would change by more than the cabinets and their lights.")
print("scene objects added:", added, "; lights moved:", [c[4] for c in CABINETS])

if COPY:
    replace_file(OBJ, newline.join(kept))
    replace_file(SCENE, updated)
    print("installed")
else:
    print("dry run: pass --copy to write")
