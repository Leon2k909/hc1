"""Verify the Fleet patch preserves unrelated records, physics and clearances."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_piles as P

folder = Path(__file__).parent
before = folder / "piles-before/Assets/models/maps/lowtide"
stage = folder / "piles-stage"


def records(path):
    rows = path.read_text().splitlines()
    vertices, textures, normals, faces, paint = [], [], [], Counter(), None
    for row in rows:
        if row.startswith("v "):
            vertices.append(tuple(map(float, row.split()[1:])))
        elif row.startswith("vt "):
            textures.append(tuple(map(float, row.split()[1:])))
        elif row.startswith("vn "):
            normals.append(tuple(map(float, row.split()[1:])))
        elif row.startswith("usemtl "):
            paint = row.split()[1]
        elif row.startswith("f "):
            tri = []
            for token in row.split()[1:]:
                v, t, n = map(int, token.split("/"))
                tri.append((vertices[v-1], textures[t-1], normals[n-1]))
            faces[(paint, tuple(tri))] += 1
    return rows, vertices, textures, normals, faces


old = records(before / "lowtide_fleet.obj")
new = records(stage / "lowtide_fleet.obj")
original_piles = records(stage / "original-piles.obj")
replacement_piles = records(stage / "replacement-piles.obj")
for index in (1, 2, 3):
    assert new[index][:len(old[index])] == old[index], "Original OBJ data changed"
    assert new[index][len(old[index]):] == replacement_piles[index]

# The old generated pile UV offset differs from Fleet's. Remove by exact paint
# and vertex positions, then compare every retained UV and normal independently.
expected_old = Counter((paint, tuple(v for v, uv, n in tri)) for (paint, tri), count in original_piles[4].items() for _ in range(count))
retained = old[4].copy()
for key, count in old[4].items():
    paint, tri = key
    match = (paint, tuple(v for v, uv, n in tri))
    take = min(expected_old[match], count)
    retained[key] -= take
    expected_old[match] -= take
assert not +expected_old
assert new[4] == +retained + replacement_piles[4], "Unrelated face, UV or normal changed"
vmdl = (stage / "lowtide_fleet.vmdl").read_text()
for paint in P.PAINTS:
    remap = f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{P.RESOURCE}/{paint}.vmat" }},\n'
    assert vmdl.count(remap) == 1
    vmdl = vmdl.replace(remap, "")
assert vmdl == (before / "lowtide_fleet.vmdl").read_text(), "Physics or model declarations changed"
for hull in before.glob("*_hulls_*.obj"):
    assert hull.read_bytes() == (K.ASSETS / "models/maps/lowtide" / hull.name).read_bytes()

minimum_alignment = 1.0
for paint, tri in replacement_piles[4]:
    points = np.asarray([v for v, uv, n in tri])
    normals = np.asarray([n for v, uv, n in tri])
    uv = np.asarray([uv for v, uv, n in tri])
    normal = np.cross(points[1]-points[0], points[2]-points[0])
    assert np.linalg.norm(normal) > 1e-6
    normal /= np.linalg.norm(normal)
    alignment = float((normals@normal).min())
    assert alignment > 0, (paint, alignment)
    assert np.allclose(np.linalg.norm(normals, axis=1), 1, atol=.002)
    assert np.isfinite(points).all() and np.isfinite(uv).all()
    minimum_alignment = min(minimum_alignment, alignment)

bounds = []
for e, n in P.POSITIONS:
    model = K.Model()
    P.cluster(model, e, n, -148)
    pts = np.asarray([p for groups in model.polygons.values() for face, _ in groups for p in face])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    assert np.all(lo >= (e-15, n-15, -148)) and np.all(hi <= (e+15, n+15, -8)), (lo, hi)
    bounds.append({"centre": [e, n], "minimum": lo.tolist(), "maximum": hi.tolist()})
report = {"clusters": 6, "posts": 18, "original_vertices_uvs_normals_retained": True,
    "unrelated_faces_retained": True, "physics_and_model_declarations_retained": True,
    "all_geometry_within_original_collision_boxes": True, "minimum_normal_alignment": minimum_alignment,
    "new_triangles": sum(replacement_piles[4].values()), "bounds": bounds}
(folder / "pile-scope-checks.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({k: v for k, v in report.items() if k != "bounds"}, indent=2))
