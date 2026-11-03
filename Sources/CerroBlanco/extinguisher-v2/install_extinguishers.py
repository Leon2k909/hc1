"""Swap Cerro Blanco's crude wall extinguishers for Railhead's extinguisher-v2: python install_extinguishers.py <project root> [--write]

Cuts each old one's faces from the OBJ the fit-out detail model really builds from, and adds an "Extinguishers" group to cerroblanco.scene, renderers only, as the old ones had no
collision. Each old one is rebuilt from the fit-out's own numbers, on the wall it stands on, and must lose exactly its triangles with every corner matching, or nothing is written.
Without --write it only reports. Files are moved into place with os.replace, and the originals are kept in before-install. No full map run. The scene is edited as text and checked
to differ only by the new group.
"""
import json
import math
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
import cerroblanco_extinguishers as E  # noqa: E402
import cerroblanco_fitout as F  # noqa: E402
import cerroblanco_parts as P  # noqa: E402

VMDL = "Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.vmdl"
SCENE = "Assets/scenes/maps/CerroBlanco/cerroblanco.scene"
WORK = os.path.join(ROOT, "output/asset-improvement-20261030/cerroblanco-extinguisher")
BACKUP = os.path.join(WORK, "before-install")
NAMESPACE = "7d2e9b41-3c58-4a6f-b1e0-5f93c8a2d714"  # Tools/cerroblanco_map.py's ids.
UP = F.UP
# Each old body's axis in engine x, y, its middle's height, and the way it faces in engine x, y, read from cerroblanco_fitout_fine.obj.
BODIES = (
    (-102.0, 1103.6, 44.0, (0, -1)), (-102.0, 1103.6, 224.0, (0, -1)), (40.0, -502.4, 44.0, (0, -1)), (692.6, -1058.0, 44.0, (-1, 0)),
    (692.6, -1058.0, 224.0, (-1, 0)), (-942.0, -502.4, 44.0, (0, -1)), (-1022.4, 972.0, 44.0, (-1, 0)),
)


def old_extinguisher(m, base, out):
    """ cerroblanco_fitout.door_fittings' extinguisher as it was. """
    side, right, up = F.frame_axes(out)
    m.oriented_box(base + out * 0.6, (side, out, up), (4.0, 1.2, 6.0), "cbf_track")
    body = base + out * 4.4
    P.rod(m, body - UP * 8, body + UP * 8, 3.1, P.RED, sides=12, caps=True)
    P.rod(m, body + UP * 8, body + UP * 10.5, 1.1, P.BLACK, sides=8, caps=True)
    P.rod(m, body + UP * 9 + right * 1.0, body + right * 3.6 - UP * 4, 0.45, P.BLACK, sides=6)


vmdl_text = open(os.path.join(ROOT, VMDL), encoding="utf-8").read()
found = re.findall(r'filename = "([^"]+\.obj)"', vmdl_text)
if len(found) != 1:
    sys.exit(f"The fit-out detail model names {found}, not one OBJ. Nothing written.")
OBJ = "Assets/" + found[0]
obj_path = os.path.join(ROOT, OBJ)
with open(obj_path, encoding="utf-8", newline="") as h:
    lines = h.readlines()
vertices, current, rows = [], None, []
for n, line in enumerate(lines):
    if line.startswith("v "):
        a, b, c = line[2:].split()[:3]
        vertices.append((float(c), float(a), float(b)))  # OBJ (a, b, c) is engine (c, a, b).
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current in ("cbf_track", P.RED, P.BLACK):
        rows.append((n, current, [int(t.split("/")[0]) - 1 for t in line.split()[1:]]))
vertices = np.array(vertices)
middle = np.array([vertices[r[2]].mean(0) for r in rows])

drop, placed, report = set(), [], []
for x, y, z, (ox, oy) in BODIES:
    # World ( x north, y west ) is plan ( e = -y, n = x ).
    out = np.array((-oy, ox, 0.0), float)
    body = np.array((-y, x, z), float)
    base = body - out * 4.4
    model = K.Model()
    old_extinguisher(model, base, out)
    want = {paint: sum(len(points) - 2 for points, *_ in polygons) for paint, polygons in model.polygons.items()}
    corners = np.array([K.to_world(p) for polygons in model.polygons.values() for points, *_ in polygons for p in points], float)
    tree = cKDTree(corners)
    got, mine = {}, []
    for k in np.nonzero(np.linalg.norm(middle - corners.mean(0), axis=1) < 30)[0]:
        n, paint, index = rows[k]
        if paint in want and tree.query(vertices[index])[0].max() < 0.03:
            got[paint] = got.get(paint, 0) + len(index) - 2
            mine.append(n)
    if got != want:
        sys.exit(f"The old extinguisher at {x}, {y}, {z} should lose {want} but matched {got}. Nothing written.")
    if drop & set(mine):
        sys.exit(f"Two extinguishers claim the same faces at {x}, {y}, {z}. Nothing written.")
    drop.update(mine)
    E.record(tuple(base + np.array((0.0, 0.0, -8.0))), out)
    world, yaw = E.PLACED[-1]
    placed.append((world, yaw))
    report.append(dict(at=list(world), yaw=yaw, out=[ox, oy], old_axis=[x, y, z], triangles=len(mine)))
    print(world, "yaw", round(yaw), "cut", want, flush=True)
print("extinguishers", len(placed), "triangles to cut", len(drop), flush=True)
os.makedirs(WORK, exist_ok=True)
json.dump(report, open(os.path.join(WORK, "placements.json"), "w"), indent=1)
kept = [line for n, line in enumerate(lines) if n not in drop]

scene_path = os.path.join(ROOT, SCENE)
text = open(scene_path, "rb").read().decode("utf-8")
scene = json.loads(text)
if '"Name": "Extinguishers"' in text:
    sys.exit("The scene already has an Extinguishers group. Nothing written.")
group = E.scene_group(K.SceneIds(NAMESPACE), placed)
at = text.index('"Name": "Cerro Blanco"')
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
body_text = json.dumps(group, indent=2, ensure_ascii=False).replace("\n", "\n" + indent)
updated = head + ",\n" + indent + body_text + closing + text[end:]
check = json.loads(updated)
world_old = next(o for o in scene["GameObjects"] if o.get("Name") == "Cerro Blanco")
world_new = next(o for o in check["GameObjects"] if o.get("Name") == "Cerro Blanco")
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
for path in (scene_path, obj_path):
    backup = os.path.join(BACKUP, os.path.basename(path))
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
temporary = scene_path + ".installing"
with open(temporary, "wb") as h:
    h.write(updated.encode("utf-8"))
os.replace(temporary, scene_path)
temporary = obj_path + ".installing"
with open(temporary, "w", encoding="utf-8", newline="") as h:
    h.writelines(kept)
os.replace(temporary, obj_path)
print("written", flush=True)
