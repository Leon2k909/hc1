"""Swap Riverdale's blocky wall extinguishers for Railhead's extinguisher-v2: python install_extinguishers.py <project root> [--write]

Cuts each old one's faces from the two OBJs the hall's models build from, and adds an "Extinguishers" group to riverdale.scene, renderers only, as the old ones had no collision.
Each old one is rebuilt from the hall's own numbers, trying the wall it could stand on, and must lose exactly its triangles with every corner matching, or nothing is written.
Without --write it only reports. Files are moved into place with os.replace, and the originals are kept in before-install. No full map run. The scene is edited as text, as it
doesn't survive a round trip through json byte for byte, and the result is checked to differ only by the new group.
"""
import json
import os
import re
import shutil
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import riverdale_extinguishers as E  # noqa: E402
import riverdale_hall as H  # noqa: E402

P, UP = H.P, H.UP
MODELS = {"d": "Assets/models/maps/riverdale/riverdale_hall_detail.obj", "fine": "Assets/models/maps/riverdale/riverdale_hall_fine.obj"}
SCENE = "Assets/scenes/maps/Riverdale/riverdale.scene"
WORK = os.path.join(ROOT, "output/asset-improvement-20261030/riverdale-extinguisher")
BACKUP = os.path.join(WORK, "before-install")
NAMESPACE = "5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85"  # Tools/riverdale_map.py's ids.
# Each old body's axis in engine x, y and its foot, read from the 120-triangle red bodies in riverdale_hall_detail.obj.
BODIES = (
    (1181.8, 872.0, 314.0), (1621.0, 635.8, 30.0), (1181.8, -872.0, 314.0), (1621.0, -635.8, 30.0), (-150.0, 995.8, 30.0), (1090.0, 995.8, 30.0), (1700.0, 995.8, 30.0),
    (600.0, 995.8, 318.0), (1300.0, 995.8, 318.0), (-172.0, -995.8, 30.0), (1090.0, -995.8, 30.0), (1700.0, -995.8, 30.0), (600.0, -995.8, 318.0), (1300.0, -995.8, 318.0),
    (1995.8, -545.0, 30.0), (1995.8, 545.0, 30.0), (1995.8, 420.0, 318.0), (1995.8, -420.0, 318.0), (-195.8, 140.0, 30.0), (-195.8, -140.0, 30.0), (1204.2, 850.0, 318.0),
    (1204.2, -850.0, 318.0),
)


def old_extinguisher(d, fine, face, s, z):
    """ riverdale_hall.extinguisher as it was. """
    c = face.p(s, 0, 4.2)
    P.lathe(d, c, [(3.3, z), (3.6, z + 0.8), (3.6, z + 16.5), (3.0, z + 18.6), (1.3, z + 19.8), (1.0, z + 20.6)], "rv_hall_red", 12)
    head = face.p(s, z + 21.6, 4.2)
    P.obox(fine, head, face.a, (2.4, 2.0, 2.0), "rv_dark")
    H.bar(fine, head + UP * 1.2 - face.a * 0.6, head + UP * 1.7 + face.a * 3.5, 0.9, 0.35, "rv_dark")
    P.pipe(fine, [head + face.a * 1.2, head + face.a * 3.4 - UP * 1.5, face.p(s + 3.9, z + 11, 4.2)], 0.45, "rv_black", 5, caps=False)
    face.box(fine, s - 1.6, s + 1.6, z + 10, z + 15, 0, 0.9, "rv_dark")
    H.sign_on(fine, face, "fire_ext", s, z + 34, 10)


class Obj:
    def __init__(self, relative):
        self.path = os.path.join(ROOT, relative)
        with open(self.path, encoding="utf-8", newline="") as h:
            self.lines = h.readlines()
        vertices, current, rows = [], None, []
        for n, line in enumerate(self.lines):
            if line.startswith("v "):
                a, b, c = line[2:].split()[:3]
                vertices.append((float(c), float(a), float(b)))  # OBJ (a, b, c) is engine (c, a, b).
            elif line.startswith("usemtl"):
                current = line.split()[1]
            elif line.startswith("f ") and current in ("rv_hall_red", "rv_dark", "rv_black", "rv_hall_signs"):
                rows.append((n, current, [int(t.split("/")[0]) - 1 for t in line.split()[1:]]))
        self.vertices = np.array(vertices)
        self.rows = rows
        self.middle = np.array([self.vertices[r[2]].mean(0) for r in rows])


files = {key: Obj(relative) for key, relative in MODELS.items()}
drops = {key: set() for key in MODELS}
placed, report = [], []
for x, y, z in BODIES:
    plan = np.array((-y, x, 0.0))
    best = None
    for out in ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)):
        o = plan - np.array((out[0], out[1], 0.0)) * 4.2
        face = H.Face(o, out)
        built = {"d": K.Model(), "fine": K.Model()}
        old_extinguisher(built["d"], built["fine"], face, 0.0, z)
        result, whole = {}, True
        for key, model in built.items():
            want = {paint: sum(len(points) - 2 for points, *_ in polygons) for paint, polygons in model.polygons.items()}
            corners = np.array([K.to_world(p) for polygons in model.polygons.values() for points, *_ in polygons for p in points], float)
            tree = cKDTree(corners)
            obj = files[key]
            near = np.nonzero(np.linalg.norm(obj.middle - corners.mean(0), axis=1) < 45)[0]
            got, lines = {}, []
            for k in near:
                n, paint, index = obj.rows[k]
                if paint in want and tree.query(obj.vertices[index])[0].max() < 0.02:
                    got[paint] = got.get(paint, 0) + len(index) - 2
                    lines.append(n)
            result[key] = lines
            whole = whole and got == want
        if whole:
            best = (out, o, result, face)
            break
    if best is None:
        sys.exit(f"The old extinguisher at {x}, {y}, {z} doesn't match on any wall. Nothing written.")
    out, o, result, face = best
    for key, lines in result.items():
        if drops[key] & set(lines):
            sys.exit(f"Two extinguishers claim the same faces at {x}, {y}, {z}. Nothing written.")
        drops[key].update(lines)
    world = tuple(float(v) for v in K.to_world((o[0], o[1], z)))
    yaw = K.plan_yaw(out) % 360.0
    placed.append((world, yaw))
    heading = K.to_world((out[0], out[1], 0.0))
    report.append(dict(at=world, yaw=yaw, out=[float(heading[0]), float(heading[1])], triangles={k: len(v) for k, v in result.items()}))
    print(world, "yaw", round(yaw), {k: len(v) for k, v in result.items()}, flush=True)
print("extinguishers", len(placed), "triangles to cut", {k: len(v) for k, v in drops.items()}, flush=True)
os.makedirs(WORK, exist_ok=True)
json.dump(report, open(os.path.join(WORK, "placements.json"), "w"), indent=1)

new_lines = {key: [line for n, line in enumerate(files[key].lines) if n not in drops[key]] for key in MODELS}

# The scene: the group goes last in the Riverdale object's children, as text.
scene_path = os.path.join(ROOT, SCENE)
raw = open(scene_path, "rb").read()
text = raw.decode("utf-8")
scene = json.loads(text)
if '"Name": "Extinguishers"' in text:
    sys.exit("The scene already has an Extinguishers group. Nothing written.")
group = E.scene_group(K.SceneIds(NAMESPACE), placed)
at = text.index('"Name": "Riverdale"')
open_at = text.index('"Children": [', at) + len('"Children": [') - 1
depth, inside, escape, end = 0, False, False, None
for i in range(open_at, len(text)):
    ch = text[i]
    if inside:
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == '"':
            inside = False
    elif ch == '"':
        inside = True
    elif ch == "[":
        depth += 1
    elif ch == "]":
        depth -= 1
        if depth == 0:
            end = i
            break
head = text[:end].rstrip()
closing = text[len(head) : end]
indent = re.search(r"\n( *)\{", text[open_at:end]).group(1)
body = json.dumps(group, indent=2, ensure_ascii=False).replace("\n", "\n" + indent)
updated = head + ",\n" + indent + body + closing + text[end:]
check = json.loads(updated)
world_old = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
world_new = next(o for o in check["GameObjects"] if o.get("Name") == "Riverdale")
if world_new["Children"][-1] != json.loads(json.dumps(group)) or world_new["Children"][:-1] != world_old["Children"]:
    sys.exit("The scene's edit changed more than the new group. Nothing written.")
world_new["Children"] = world_old["Children"]
if check != scene:
    sys.exit("The scene's edit changed more than the new group. Nothing written.")
print("scene grows by", len(updated) - len(text), "characters, group of", len(group["Children"]), flush=True)
if not WRITE:
    print("report only: pass --write to change the files")
    sys.exit(0)
os.makedirs(BACKUP, exist_ok=True)
for path in [scene_path] + [obj.path for obj in files.values()]:
    backup = os.path.join(BACKUP, os.path.basename(path))
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
temporary = scene_path + ".installing"
with open(temporary, "wb") as h:
    h.write(updated.encode("utf-8"))
os.replace(temporary, scene_path)
for key, obj in files.items():
    temporary = obj.path + ".installing"
    with open(temporary, "w", encoding="utf-8", newline="") as h:
        h.writelines(new_lines[key])
    os.replace(temporary, obj.path)
print("written", flush=True)
