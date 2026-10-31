"""Swap Lowtide's twelve quay bollards for mooring_bollard_v2 without regenerating the map: python -X utf8 install_bollards.py <project root>

Rerunning Tools/lowtide_map.py isn't safe: other tools have passed over its output, and an unchanged dry run differs from the live files in 14 models and
262 scene objects. So this asks the map's code where the bollards are, cuts only their iron_black faces out of the checked-in dressing OBJs, moves the two
collision boxes by the crane's legs in the dressing vmdls, and adds the same "Quay Bollards" group to the scene that write_scene makes. Everything is worked
out before anything is written, each file is swapped in whole, and it stops if a bollard doesn't have the faces it should. Safe to rerun.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import lowtide_map as M  # noqa: E402

K = M.K
BASE = os.path.join(ROOT, "Assets", "models", "maps", "lowtide")
OLD_N = -1580.0
FACES_EACH = 102


def swap_in(path, data, stamp):
    """Writes beside the file and replaces it in one step, unless someone else has changed it since it was read."""
    if os.stat(path).st_mtime_ns != stamp:
        raise SystemExit(f"{path} changed while this ran: run it again.")
    incoming = path + ".bollard-incoming"
    with open(incoming, "wb") as h:
        h.write(data)
    os.replace(incoming, path)


def cut_faces(path, spots):
    """The OBJ's text without the bollards' faces, and how many each spot lost. A usemtl left with no faces goes too."""
    with open(path, encoding="utf-8", newline="") as h:
        lines = h.readlines()
    verts = []
    for line in lines:
        if line.startswith("v "):
            a, b, c = line[2:].split()[:3]
            verts.append((float(a), float(b), float(c)))
    verts = np.array(verts)
    # OBJ (a, b, c) is engine (c, a, b), and plan (e, n, z) is engine (n, -e, z).
    east, north, up = -verts[:, 0], verts[:, 2], verts[:, 1]
    current = None
    group = None
    faces_in_group, cut_in_group = {}, {}
    drop = set()
    counts = [0] * len(spots)
    for n, line in enumerate(lines):
        if line.startswith("usemtl"):
            current = line.split()[1]
            group = n
        elif line.startswith("f "):
            faces_in_group[group] = faces_in_group.get(group, 0) + 1
            if current != "iron_black":
                continue
            corners = np.array([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
            for k, (e, spot_n) in enumerate(spots):
                reach = np.hypot(east[corners] - e, north[corners] - spot_n).max()
                if reach < 9.5 and up[corners].min() > -0.5 and up[corners].max() < 25.5:
                    drop.add(n)
                    counts[k] += 1
                    cut_in_group[group] = cut_in_group.get(group, 0) + 1
                    break
    drop |= {g for g, cut in cut_in_group.items() if g is not None and cut == faces_in_group[g]}
    return "".join(line for n, line in enumerate(lines) if n not in drop), counts


plans = []
for side, sign in (("east", 1), ("west", -1)):
    obj = os.path.join(BASE, f"lowtide_dress_{side}.obj")
    stamp = os.stat(obj).st_mtime_ns
    spots = [(e, OLD_N) for e, _ in M.quay_bollards(sign)]
    text, counts = cut_faces(obj, spots)
    print(f"{side}: faces per bollard {counts}", flush=True)
    if any(c != FACES_EACH for c in counts) and any(counts):
        raise SystemExit(f"{side}: each bollard should have {FACES_EACH} faces or none, not {counts}. Nothing written.")
    if any(counts):
        plans.append((obj, text.encode("utf-8"), stamp))

    # The collision boxes of those that moved. Only these change: the rest stand where they did.
    vmdl = os.path.join(BASE, f"lowtide_dress_{side}.vmdl")
    stamp = os.stat(vmdl).st_mtime_ns
    with open(vmdl, "rb") as h:
        data = before = h.read()
    for e, n in M.quay_bollards(sign):
        if n == OLD_N:
            continue
        old = f"origin = [ {OLD_N:.4f}, {-e:.4f}, 12.5000 ]".encode()
        new = f"origin = [ {n:.4f}, {-e:.4f}, 12.5000 ]".encode()
        if data.count(new) == 1 and data.count(old) == 0:
            continue
        if data.count(old) != 1:
            raise SystemExit(f"{vmdl}: expected one collision box at {old.decode()}. Nothing written.")
        data = data.replace(old, new)
        print(f"{side}: collision box moved to {new.decode()}", flush=True)
    if data != before:
        plans.append((vmdl, data, stamp))

scene_file = str(M.SCENE_FILE)
stamp = os.stat(scene_file).st_mtime_ns
with open(scene_file, "rb") as h:
    raw = h.read()
scene = json.loads(raw.decode("utf-8"))
newline = "\r\n" if b"\r\n" in raw else "\n"
if json.dumps(scene, indent=2).replace("\n", newline).encode("utf-8") != raw:
    raise SystemExit("The scene doesn't survive being read and written unchanged, so writing it would change more than the bollards. Nothing written.")
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Lowtide")
group = K.game_object(M.ids, "Quay Bollards", "world/bollards", children=[M.bollard_object(e, n) for s in (1, -1) for e, n in M.quay_bollards(s)])
children = world["Children"]
names = [c.get("Name") for c in children]
if "Quay Bollards" in names:
    children[names.index("Quay Bollards")] = group
else:
    children.append(group)
plans.append((scene_file, json.dumps(scene, indent=2).replace("\n", newline).encode("utf-8"), stamp))

for path, data, stamp in plans:
    swap_in(path, data, stamp)
    print("wrote", os.path.relpath(path, ROOT), flush=True)
print(len(group["Children"]), "bollards in the scene")
