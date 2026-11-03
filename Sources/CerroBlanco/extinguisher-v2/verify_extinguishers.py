"""Are Cerro Blanco's old extinguishers really gone, and do the new ones agree with the map script? python verify_extinguishers.py <project root> [--build]

Reads the files as they are now, as other sessions write them too. --build also runs the map's build in memory, writing nothing, and compares where it would place them. Exit 1 on any fault.
"""
import json
import os
import re
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import cerroblanco_extinguishers as E  # noqa: E402
import cerroblanco_fitout as F  # noqa: E402
import cerroblanco_parts as P  # noqa: E402

places = json.load(open(os.path.join(ROOT, "output/asset-improvement-20261030/cerroblanco-extinguisher/placements.json")))
UP = F.UP


def old_extinguisher(m, base, out):
    """ cerroblanco_fitout.door_fittings' extinguisher as it was, to look for what's left of it. """
    side, right, up = F.frame_axes(out)
    m.oriented_box(base + out * 0.6, (side, out, up), (4.0, 1.2, 6.0), "cbf_track")
    body = base + out * 4.4
    P.rod(m, body - UP * 8, body + UP * 8, 3.1, P.RED, sides=12, caps=True)
    P.rod(m, body + UP * 8, body + UP * 10.5, 1.1, P.BLACK, sides=8, caps=True)
    P.rod(m, body + UP * 9 + right * 1.0, body + right * 3.6 - UP * 4, 0.45, P.BLACK, sides=6)


text = open(os.path.join(ROOT, "Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.vmdl"), encoding="utf-8").read()
found = re.findall(r'filename = "([^"]+\.obj)"', text)
print("fit-out detail builds from", found, flush=True)
vertices, current, rows = [], None, []
for line in open(os.path.join(ROOT, "Assets", found[0]), encoding="utf-8"):
    if line.startswith("v "):
        a, b, c = line[2:].split()[:3]
        vertices.append((float(c), float(a), float(b)))
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current in ("cbf_track", P.RED, P.BLACK):
        rows.append((current, [int(t.split("/")[0]) - 1 for t in line.split()[1:]]))
vertices = np.array(vertices)
middle = np.array([vertices[r[1]].mean(0) for r in rows])
left = 0
for place in places:
    x, y, z = place["old_axis"]
    ox, oy = place["out"]
    out = np.array((-oy, ox, 0.0), float)
    model = K.Model()
    old_extinguisher(model, np.array((-y, x, z), float) - out * 4.4, out)
    corners = np.array([K.to_world(p) for polygons in model.polygons.values() for points, *_ in polygons for p in points], float)
    tree = cKDTree(corners)
    for k in np.nonzero(np.linalg.norm(middle - corners.mean(0), axis=1) < 30)[0]:
        paint, index = rows[k]
        if paint in model.polygons and tree.query(vertices[index])[0].max() < 0.03:
            left += 1
scene = json.load(open(os.path.join(ROOT, "Assets/scenes/maps/CerroBlanco/cerroblanco.scene"), encoding="utf-8"))
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Cerro Blanco")
group = [c for c in world["Children"] if c.get("Name") == "Extinguishers"]
children = group[0]["Children"] if group else []
print("old faces left", left, "| groups", len(group), "placed", len(children), flush=True)
same = True
if "--build" in sys.argv:
    import cerroblanco_map as M  # noqa: E402

    E.PLACED.clear()
    M.build()
    got = {(round(w[0], 1), round(w[1], 1), round(w[2], 1), round(y) % 360) for w, y in E.PLACED}
    need = {(round(p["at"][0], 1), round(p["at"][1], 1), round(p["at"][2], 1), round(p["yaw"]) % 360) for p in places}
    same = got == need
    print("map script places", len(E.PLACED), "same as the install", same, "| only script", sorted(got - need)[:6], "| only install", sorted(need - got)[:6], flush=True)
sys.exit(0 if left == 0 and len(group) == 1 and len(children) == len(places) and same else 1)
