"""Check the install from the files, with no editor: python -X utf8 verify_board.py <project root>

The old boards' faces are gone and nothing else near them, the OBJs still read as whole meshes, the scene holds the five new boards exactly where the old ones stood, and the model
and material are compiled. Says whether the hall's models have recompiled since, which needs an open editor. Reads only.
"""
import json
import math
import os
import re
import sys
from collections import Counter

ROOT = sys.argv[1]
BASE = os.path.join(ROOT, "Assets", "models", "maps", "riverdale")
KEEP = os.path.join(ROOT, "output", "asset-improvement-20261030", "notice-board", "before-install")
# Engine (x, y, z) of each old board's bottom centre on the wall, and its yaw.
SPOTS = (((1205, 1000, 46), -90), ((1205, -1000, 46), 90), ((2000, -95, 46), 180), ((1200, 670, 346), 0), ((1200, -670, 346), 0))
problems = []


def read(path):
    verts, faces, current = [], Counter(), None
    tris = []
    uvs = normals = 0
    for line in open(path, encoding="utf-8"):
        if line.startswith("v "):
            a, b, c = map(float, line[2:].split()[:3])
            verts.append((c, a, b))
        elif line.startswith("vt"):
            uvs += 1
        elif line.startswith("vn"):
            normals += 1
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f "):
            faces[current] += 1
            tris.append((current, line.split()[1:]))
    return verts, faces, tris, uvs, normals


for name, paint, per_board in (("riverdale_hall_detail.obj", "rv_frame", 10), ("riverdale_hall_fine.obj", "rv_hall_signs", 2)):
    verts, faces, tris, uvs, normals = read(os.path.join(BASE, name))
    bad = left = 0
    for mat, toks in tris:
        ids = [t.split("/") for t in toks]
        for t in ids:
            if not 1 <= int(t[0]) <= len(verts) or (len(t) > 1 and t[1] and not 1 <= int(t[1]) <= uvs) or (len(t) > 2 and t[2] and not 1 <= int(t[2]) <= normals):
                bad += 1
        if mat != paint:
            continue
        p = [verts[int(t[0]) - 1] for t in ids]
        for (x, y, z), yaw in SPOTS:
            a = math.radians(yaw)
            out = [(q[0] - x) * math.cos(a) + (q[1] - y) * math.sin(a) for q in p]
            along = [-(q[0] - x) * math.sin(a) + (q[1] - y) * math.cos(a) for q in p]
            if max(map(abs, along)) <= 18.02 and min(out) >= -0.02 and max(out) <= 1.3 and min(q[2] for q in p) >= z - 0.02 and max(q[2] for q in p) <= z + 24.02:
                left += 1
    before = read(os.path.join(KEEP, name))[1]
    changed = {k: faces.get(k, 0) - before.get(k, 0) for k in set(faces) | set(before) if faces.get(k, 0) != before.get(k, 0)}
    print(name, "| bad indices", bad, "| old board faces left", left, "| material counts changed", changed)
    if bad or left or changed != {paint: -5 * per_board}:
        problems.append(name)

scene = json.loads(open(os.path.join(ROOT, "Assets", "scenes", "maps", "Riverdale", "riverdale.scene"), encoding="utf-8").read())
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
group = next(c for c in world["Children"] if c.get("Name") == "Notice Boards")
guids = []


def walk(objs):
    for o in objs:
        guids.append(o.get("__guid"))
        for c in o.get("Components") or []:
            guids.append(c.get("__guid"))
        walk(o.get("Children") or [])


walk(scene["GameObjects"])
repeats = [k for k, n in Counter(guids).items() if n > 1 and k]
print("scene: boards", len(group["Children"]), "| repeated ids", len(repeats))
if repeats:
    problems.append("repeated ids")
for item, ((x, y, z), yaw) in zip(group["Children"], SPOTS):
    px, py, pz = map(float, item["Position"].split(","))
    qx, qy, qz, qw = map(float, item["Rotation"].split(","))
    got = math.degrees(2 * math.atan2(qz, qw))
    turn = (got - yaw + 180) % 360 - 180
    model = item["Components"][0]["Model"]
    ok = abs(px - x) < 0.01 and abs(py - y) < 0.01 and abs(pz - z) < 0.01 and abs(turn) < 0.01 and "notice_board_v2" in model
    print(" ", item["Position"], f"yaw {got:.0f}", "ok" if ok else "WRONG")
    if not ok:
        problems.append(item["Position"])

for rel in ("models/maps/riverdale/notice_board_v2/notice_board.vmdl", "materials/riverdale/notice_board_v2/notice_board.vmat"):
    full = os.path.join(ROOT, "Assets", *rel.split("/"))
    fresh = os.path.exists(full + "_c") and os.path.getmtime(full + "_c") >= os.path.getmtime(full)
    print(rel, "compiled" if fresh else "NOT COMPILED")
    if not fresh:
        problems.append(rel)

# The source's own material comes through untouched.
for name in ("riverdale_hall_detail", "riverdale_hall_fine"):
    source, built = os.path.join(BASE, name + ".obj"), os.path.join(BASE, name + ".vmdl_c")
    print(name, "recompiled since the cut" if os.path.getmtime(built) >= os.path.getmtime(source) else "NOT recompiled yet: needs s&box open")

text = open(os.path.join(ROOT, "Tools", "riverdale_hall.py"), encoding="utf-8").read()
body = re.search(r"def notice_board\(.*?\n\n", text, re.S).group(0)
print("riverdale_hall.notice_board draws nothing:", "fine" not in body.split("\n", 1)[1].replace('"""', "") or "NOTICE_BOARDS.record" in body)
print("PROBLEMS:", problems or "none")
