"""Check the exported Lowtide surfaces without starting s&box."""
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "Assets"
MODELS = ASSETS / "models/maps/lowtide"
DOORS = [
    ("Fleet north", (240, 260, 815, 895)),
    ("Fleet south", (240, 260, -95, -15)),
    ("street north", (980, 1000, 805, 905)),
    ("street south", (980, 1000, -105, -5)),
    ("north end", (560, 680, 1130, 1150)),
    ("south end", (560, 680, -400, -380)),
]


def read_mesh(path):
    vertices, uvs, faces, materials = [], [], [], set()
    material = None
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            x, y, z = map(float, fields[1:])
            vertices.append((-x, z, y))  # OBJ axes back to east, north, height.
        elif fields[0] == "vt":
            uvs.append(tuple(map(float, fields[1:])))
        elif fields[0] == "usemtl":
            material = fields[1]
            materials.add(material)
        elif fields[0] == "f":
            indices = [tuple(int(x) - 1 for x in field.split("/")) for field in fields[1:]]
            faces.append((material, indices))
    points, texcoords = np.asarray(vertices), np.asarray(uvs)
    floor = []
    for material, indices in faces:
        if material not in {"ashlar_grey", "rw_concrete"}:
            continue
        tri = points[[index[0] for index in indices]]
        if not np.allclose(tri[:, 2], 0) or np.cross(tri[1] - tri[0], tri[2] - tri[0])[2] <= 0:
            continue
        uv = texcoords[[index[1] for index in indices]]
        assert np.all(np.isfinite(uv)) and abs(np.linalg.det(uv[1:] - uv[0])) > 1e-8
        floor.append(tri[:, :2])
    return points, faces, materials, np.asarray(floor)


report = {}
for side, sign in (("east", 1), ("west", -1)):
    name = "lowtide_" + side
    points, faces, materials, floor = read_mesh(MODELS / (name + ".obj"))
    checks = 0
    for label, (e0, e1, n0, n1) in DOORS:
        for e in np.linspace(e0 + .1, e1 - .1, 9):
            for n in np.linspace(n0 + .1, n1 - .1, 9):
                point = np.array((sign * e, n))
                edges = np.roll(floor, -1, axis=1) - floor
                delta = point - floor
                cross = edges[:, :, 0] * delta[:, :, 1] - edges[:, :, 1] * delta[:, :, 0]
                assert np.any(np.all(cross >= -1e-6, axis=1)), (side, label, point)
                checks += 1
    # Every pavement back and end needs a vertical rendered face above ground.
    concrete = [points[[index[0] for index in indices]] for material, indices in faces if material == "rw_concrete"]
    for e, n, axis in ((620, 1150, 1), (620, 1450, 1), (240, 1175, 0), (2700, 1175, 0),
                       (240, 1425, 0), (2700, 1425, 0)):
        point = np.array((sign * e, n, 2.5))
        assert any(np.allclose(tri[:, axis], point[axis])
                   and np.all(point >= tri.min(axis=0) - 1e-6)
                   and np.all(point <= tri.max(axis=0) + 1e-6) for tri in concrete), (side, point)
    remaps = dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"', (MODELS / (name + ".vmdl")).read_text()))
    assert materials == set(remaps), (side, materials ^ set(remaps))
    assert all((ASSETS / target).is_file() for target in remaps.values())
    report[side] = {"covered_threshold_samples": checks, "closed_pavement_edges": 6,
                    "triangles": len(faces), "valid_materials": len(materials)}

(Path(__file__).parent / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
