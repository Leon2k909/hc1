"""Check the review's geometry, UVs, normal map and protected production files."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from PIL import Image

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT / "output/asset-improvement-20261030/riverside-sandbags"
manifest = json.loads((OUT / "review.json").read_text())
for relative, expected in manifest["protected"].items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative + " changed"
rows = []
for path in sorted((ROOT / "Assets/models/props/riverside/sandbag_v2").glob("*_lod*.obj")):
    points, uv, normals, faces = [], [], [], []
    for line in path.read_text().splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v": points.append(list(map(float, p[1:])))
        elif p[0] == "vt": uv.append(list(map(float, p[1:])))
        elif p[0] == "vn": normals.append(list(map(float, p[1:])))
        elif p[0] == "f": faces.append([[int(v) - 1 for v in t.split('/')] for t in p[1:]])
    indices = np.asarray(faces)
    pos = np.asarray(points)[indices[:, :, 0]]
    tex = np.asarray(uv)[indices[:, :, 1]]
    ns = np.asarray(normals)[indices[:, :, 2]]
    cross = np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0])
    assert np.isfinite(pos).all() and np.isfinite(ns).all() and np.isfinite(tex).all()
    assert np.linalg.norm(cross, axis=-1).min() > 1e-8, path
    score = (cross * ns.mean(1)).sum(-1)
    if (score <= 0).any():
        bad = np.flatnonzero(score <= 0)
        print("Winding diagnostics", path.name, len(bad), score[bad[:3]], pos[bad[0]], ns[bad[0]], flush=True)
    assert (score > 0).all(), path
    a, b = tex[:, 1] - tex[:, 0], tex[:, 2] - tex[:, 0]
    area = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    assert abs(area).min() > 1e-10, (path, int((abs(area) < 1e-10).sum()))
    assert tex.min() >= 0 and tex.max() <= 1, (path, tex.min(), tex.max())
    rows.append(dict(mesh=path.name, triangles=len(faces), valid_geometry=True, valid_uvs=True))
normal = np.asarray(Image.open(ROOT / "Assets/materials/riverside/sandbag_v2/sandbag_normal.png"), float) / 127.5 - 1
assert np.allclose(np.linalg.norm(normal, axis=-1), 1, atol=.015)
assert normal[:, :, 2].min() > 0
report = dict(meshes=rows, bag_placements=len(manifest["bags"]), barricades=len(manifest["walls"]), production_unchanged=True, normal_map_valid=True)
(OUT / "verification.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
