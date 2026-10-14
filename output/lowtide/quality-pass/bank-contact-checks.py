"""Measure rock grounding against the actual triangulated Fleet bank asset."""
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
import lowtide_banks as B
import lowtide_marine as M
import lowtide_finish as F

vertices, faces = [], []
paint = None
for line in (L.OUT_DIR / "lowtide_fleet.obj").read_text().splitlines():
    if line.startswith("v "):
        x, y, z = map(float, line.split()[1:])
        # map_kit writes world XYZ as OBJ YZX: undo both axis conventions.
        vertices.append((-x, z, y))
    elif line.startswith("usemtl "):
        paint = line.split()[1]
    elif line.startswith("f ") and paint in ("lt_mud", "lt_mud_wet"):
        indices = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
        faces.extend((indices[0], indices[i], indices[i + 1]) for i in range(1, len(indices) - 1))
triangles = np.asarray(vertices)[np.asarray(faces)]
tree = cKDTree(triangles[:, :, :2].mean(axis=1))


def surface(e, n):
    query = np.column_stack((np.atleast_1d(e), np.atleast_1d(n)))
    _, nearest = tree.query(query, k=24)
    tri = triangles[nearest]
    a, b, c = tri[:, :, 0, :], tri[:, :, 1, :], tri[:, :, 2, :]
    u, v, q = b[..., :2] - a[..., :2], c[..., :2] - a[..., :2], query[:, None, :] - a[..., :2]
    det = u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]
    s = (q[..., 0] * v[..., 1] - q[..., 1] * v[..., 0]) / det
    t = (u[..., 0] * q[..., 1] - u[..., 1] * q[..., 0]) / det
    inside = (s >= -1e-7) & (t >= -1e-7) & (s + t <= 1 + 1e-7)
    assert inside.any(axis=1).all(), "Query leaves authored bank triangles"
    z = a[..., 2] + s * (b[..., 2] - a[..., 2]) + t * (c[..., 2] - a[..., 2])
    return np.where(inside, z, -np.inf).max(axis=1)


stones = []
original = B.cobble


def check_cobble(unused, e, n, ground, radius, height, seed, brick=False, terrain=None):
    model = K.Model()
    original(model, e, n, ground, radius, height, seed, brick, terrain)
    paint = "lt_tidal_brick" if brick else "lt_tidal_granite"
    points = np.asarray([p for tri, _ in model.polygons[paint] for p in tri])
    unique, inverse = np.unique(np.round(points, 8), axis=0, return_inverse=True)
    faces = inverse.reshape((-1, 3))
    edges = np.concatenate((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)]))
    edges.sort(axis=1)
    edges, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = np.unique(edges[counts == 1])
    distances = unique[:, 2] - surface(unique[:, 0], unique[:, 1])
    stones.append({"e": e, "n": n, "radius": radius, "bottom": float(distances.min()),
        "top": float(distances.max()), "boundary_max": float(distances[boundary].max()) if len(boundary) else None,
        "centre_surface_error": float(ground - surface(e, n)[0])})


B.cobble = check_cobble
M.banks(K.Model(), L)
F.build(L)
report = {"terrain_source": "Assets/models/maps/lowtide/lowtide_fleet.obj",
    "terrain_triangles": len(triangles), "stones": len(stones),
    "floating_stones": [s for s in stones if s["bottom"] > 0],
    "fully_buried_stones": [s for s in stones if s["top"] < 0],
    "exposed_cut_edges": [s for s in stones if s["boundary_max"] is not None and s["boundary_max"] > 0],
    "highest_cut_edge_inches": max(s["boundary_max"] for s in stones if s["boundary_max"] is not None),
    "maximum_ground_interpolation_error_inches": max(abs(s["centre_surface_error"]) for s in stones)}
path = Path(__file__).with_suffix(".json")
path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
assert not report["floating_stones"] and not report["exposed_cut_edges"]
