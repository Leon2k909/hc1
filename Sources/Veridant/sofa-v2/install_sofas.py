"""Install the sofas in the map's files: python install_sofas.py <project root> [--write]

Cuts the old sofas' faces from the OBJ veridant_buildings.vmdl really builds from, and adds the "Sofas" group to veridant.scene, renderers only, so the old collision
in the merged model stays. Every corner must be one of an old sofa's, and each sofa must lose exactly its old triangles, or nothing is written. Without --write it
only reports. Files are moved into place with os.replace, and the originals are kept in the work folder's before-install. No full map run.
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
import veridant_sofas as Sofas  # noqa: E402

BASE = os.path.join(ROOT, "Assets/models/maps/veridant/lounger-v2/veridant_buildings-base.obj")
SCENE = os.path.join(ROOT, "Assets/scenes/maps/Veridant/veridant.scene")
BACKUP = os.path.join(ROOT, "output/asset-improvement-20261030/sofa/before-install")
PAINTS = {"vr_sofa": 48, "vr_cushion": 36, "vr_black": 12}  # Triangles each old sofa has of each.
L0, L1 = 0.0, 128.0
# From Tools/veridant_map.py: plan ( e, n ), facing, length, floor.
SOFAS = (
    ((-480.0, -300.0), (0.0, 1.0), 84.0, L0),
    ((-480.0, -470.0), (0.0, 1.0), 84.0, L0),
    ((-330.0, -460.0), (-1.0, 0.0), 84.0, L0),
    ((-380.0, -300.0), (0.0, -1.0), 96.0, L1),
    ((-560.0, -300.0), (0.0, -1.0), 96.0, L1),
    ((-470.0, -470.0), (0.0, 1.0), 120.0, L1),
    ((240.0, -500.0), (1.0, 0.0), 84.0, L1),
    ((660.0, -500.0), (-1.0, 0.0), 84.0, L1),
    ((60.0, 270.0), (0.0, 1.0), 84.0, 0.0),
)


def old_corners(c, facing, length, z0):
    """ Every corner of the old sofa's boxes, from veridant_parts.sofa as it was, in engine axes. """
    f = np.array((facing[0], facing[1], 0.0))
    up = np.array((0.0, 0.0, 1.0))
    s = np.cross(up, f)
    b = np.array((c[0], c[1], z0))
    parts = [(b + up * 2, (34, length - 4, 4)), (b + up * 10, (36, length, 12)), (b - f * 14 + up * 24, (8, length, 18))]
    parts += [(b + s * (length / 2 - 4) * sg + up * 20, (36, 8, 8)) for sg in (-1, 1)]
    parts += [(b + s * ((i - 1) * (length - 12) / 3) - f * 9 + up * 26, (6, (length - 16) / 3 - 2, 14)) for i in range(3)]
    corners = []
    for centre, (a, w, h) in parts:
        for sa in (-0.5, 0.5):
            for sw in (-0.5, 0.5):
                for sh in (-0.5, 0.5):
                    p = centre + f * a * sa + s * w * sw + up * h * sh
                    corners.append(K.to_world(p))
    return np.array(corners, float)


trees = [cKDTree(old_corners(*sofa)) for sofa in SOFAS]
middles = np.array([K.to_world((c[0], c[1], z)) for c, _, _, z in SOFAS], float)

with open(BASE, encoding="utf-8", newline="") as h:
    lines = h.readlines()
v = []
for line in lines:
    if line.startswith("v "):
        a, b, c = line[2:].split()[:3]
        v.append((float(c), float(a), float(b)))  # OBJ (a, b, c) is engine (c, a, b).
v = np.array(v)
current = None
drop = set()
lost = [dict.fromkeys(PAINTS, 0) for _ in SOFAS]
for n, line in enumerate(lines):
    if line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current in PAINTS:
        tokens = line.split()[1:]
        q = v[[int(t.split("/")[0]) - 1 for t in tokens]]
        near = np.nonzero(np.linalg.norm(middles[:, :2] - q[0, :2], axis=1) < 70)[0]
        for k in near:
            if trees[k].query(q)[0].max() < 0.02:
                drop.add(n)
                lost[k][current] += len(tokens) - 2
                break
for sofa, got in zip(SOFAS, lost):
    print(sofa[0], "length", sofa[2], got)
if any(got != PAINTS for got in lost):
    sys.exit(f"Expected every sofa to lose exactly {PAINTS}. Nothing written.")
print("faces to cut:", len(drop), "of", len(lines), "lines", flush=True)
# A usemtl the cut leaves with no faces goes too. Others that were already empty stay as they were.
kept = [line for n, line in enumerate(lines) if n not in drop]
final = []
for n, line in enumerate(kept):
    if line.startswith("usemtl") and line.split()[1] in PAINTS:
        following = next((x for x in kept[n + 1 :] if x.startswith(("f ", "usemtl"))), "")
        if not following.startswith("f "):
            print("no faces left under", line.strip())
            continue
    final.append(line)

text = open(SCENE, "rb").read().decode("utf-8")
newline = "\r\n" if "\r\n" in text else "\n"
scene = json.loads(text)
namespace = re.search(r'ids = K\.SceneIds\( "([^"]+)" \)', open(os.path.join(ROOT, "Tools/veridant_map.py"), encoding="utf-8").read()).group(1)
ids = K.SceneIds(namespace)
placed = [(tuple(float(x) for x in K.to_world((c[0], c[1], z))), K.plan_yaw(f) % 360.0, int(length)) for c, f, length, z in SOFAS]
group = Sofas.scene_group(ids, placed)
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Veridant")
world["Children"] = [c for c in world["Children"] if c.get("Name") != "Sofas"] + [group]
scene_text = json.dumps(scene, indent=2, ensure_ascii=False).replace("\n", newline) + (newline if text.endswith("\n") else "")
for child in group["Children"]:
    print(child["Position"], child["Rotation"], child["Components"][0]["Model"])
print("scene grows by", len(scene_text) - len(text), "bytes", flush=True)
if not WRITE:
    print("report only: pass --write to change the files")
    sys.exit(0)
os.makedirs(BACKUP, exist_ok=True)
for path in (BASE, SCENE):
    backup = os.path.join(BACKUP, os.path.basename(path))
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
temporary = BASE + ".installing"
with open(temporary, "w", encoding="utf-8", newline="") as h:
    h.writelines(final)
os.replace(temporary, BASE)
temporary = SCENE + ".installing"
with open(temporary, "wb") as h:
    h.write(scene_text.encode("utf-8"))
os.replace(temporary, SCENE)
print("written", flush=True)
