"""Are Riverdale's old extinguishers really gone and the new ones really placed? python verify_extinguishers.py <project root>

Other sessions write the same OBJs and scene, so this reads the files as they are now. Exit 1 if any old face is back or the group is short. Writes nothing.
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
import riverdale_hall as H  # noqa: E402

P, UP = H.P, H.UP
places = json.load(open(os.path.join(ROOT, "output/asset-improvement-20261030/riverdale-extinguisher/placements.json")))


def old_extinguisher(d, fine, face, s, z):
    """ riverdale_hall.extinguisher as it was, to look for what's left of it. """
    c = face.p(s, 0, 4.2)
    P.lathe(d, c, [(3.3, z), (3.6, z + 0.8), (3.6, z + 16.5), (3.0, z + 18.6), (1.3, z + 19.8), (1.0, z + 20.6)], "rv_hall_red", 12)
    head = face.p(s, z + 21.6, 4.2)
    P.obox(fine, head, face.a, (2.4, 2.0, 2.0), "rv_dark")
    H.bar(fine, head + UP * 1.2 - face.a * 0.6, head + UP * 1.7 + face.a * 3.5, 0.9, 0.35, "rv_dark")
    P.pipe(fine, [head + face.a * 1.2, head + face.a * 3.4 - UP * 1.5, face.p(s + 3.9, z + 11, 4.2)], 0.45, "rv_black", 5, caps=False)
    face.box(fine, s - 1.6, s + 1.6, z + 10, z + 15, 0, 0.9, "rv_dark")
    H.sign_on(fine, face, "fire_ext", s, z + 34, 10)


def read(relative):
    vertices, current, rows = [], None, []
    for line in open(os.path.join(ROOT, relative), encoding="utf-8"):
        if line.startswith("v "):
            a, b, c = line[2:].split()[:3]
            vertices.append((float(c), float(a), float(b)))
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current in ("rv_hall_red", "rv_dark", "rv_black", "rv_hall_signs"):
            rows.append((current, [int(t.split("/")[0]) - 1 for t in line.split()[1:]]))
    vertices = np.array(vertices)
    return vertices, rows, np.array([vertices[r[1]].mean(0) for r in rows])


def built_from(name):
    """ The OBJ a model really builds from now, as other installs repoint them. """
    text = open(os.path.join(ROOT, "Assets/models/maps/riverdale", name + ".vmdl"), encoding="utf-8").read()
    found = re.findall(r'filename = "([^"]+\.obj)"', text)
    if len(found) != 1:
        sys.exit(f"{name}.vmdl names {found}, not one OBJ: look at it by hand.")
    print(name, "builds from", found[0], flush=True)
    return "Assets/" + found[0]


files = {"d": read(built_from("riverdale_hall_detail")), "fine": read(built_from("riverdale_hall_fine"))}
left = 0
for place in places:
    x, y, z = place["at"]
    ox, oy = place["out"]
    # Back to plan: world ( x north, y west ) is plan ( e = -y, n = x ).
    o, out = np.array((-y, x, 0.0)), (-oy, ox)
    built = {"d": K.Model(), "fine": K.Model()}
    old_extinguisher(built["d"], built["fine"], H.Face(o, out), 0.0, z)
    for key, model in built.items():
        corners = np.array([K.to_world(p) for polygons in model.polygons.values() for points, *_ in polygons for p in points], float)
        tree = cKDTree(corners)
        vertices, rows, middle = files[key]
        for k in np.nonzero(np.linalg.norm(middle - corners.mean(0), axis=1) < 45)[0]:
            paint, index = rows[k]
            if paint in model.polygons and tree.query(vertices[index])[0].max() < 0.02:
                left += 1
scene = json.load(open(os.path.join(ROOT, "Assets/scenes/maps/Riverdale/riverdale.scene"), encoding="utf-8"))
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
group = [c for c in world["Children"] if c.get("Name") == "Extinguishers"]
children = group[0]["Children"] if group else []
models = {c["Components"][0]["Model"] if isinstance(c["Components"][0]["Model"], str) else c["Components"][0]["Model"].get("Path") for c in children}
print("old faces left", left, "| groups", len(group), "placed", len(children), "models", models, flush=True)
sys.exit(0 if left == 0 and len(group) == 1 and len(children) == len(places) else 1)
