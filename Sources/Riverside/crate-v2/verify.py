"""Verify review mesh UVs, winding, normal maps, and unchanged live Riverside files."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from PIL import Image

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT / "output/asset-improvement-20261030/riverside-crate"
plan = json.loads((OUT / "review-config.json").read_text())
for relative, key in (("Assets/models/maps/riverside/riverside_pad.obj", "pad_sha256"),
                      ("Assets/scenes/maps/Riverside/riverside.scene", "scene_sha256")):
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == plan[key], relative + " changed since the review snapshot"

report = []
for lod in range(3):
    vertices, uvs, normals, faces = [], [], [], []
    for line in (ROOT / f"Assets/models/props/riverside/crate_v2/crate_lod{lod}.obj").read_text().splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            vertices.append(list(map(float, p[1:])))
        elif p[0] == "vt":
            uvs.append(list(map(float, p[1:])))
        elif p[0] == "vn":
            normals.append(list(map(float, p[1:])))
        elif p[0] == "f":
            faces.append([[int(i) - 1 for i in t.split("/")] for t in p[1:]])
    indices = np.asarray(faces)
    p = np.asarray(vertices)[indices[:, :, 0]]
    uv = np.asarray(uvs)[indices[:, :, 1]]
    n = np.asarray(normals)[indices[:, :, 2]]
    assert np.isfinite(p).all() and np.isfinite(uv).all() and np.isfinite(n).all()
    assert uv.min() >= 0 and uv.max() <= 1
    area = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    assert (np.linalg.norm(area, axis=1) > 1e-7).all()
    assert ((area * n.mean(1)).sum(-1) > 0).all()
    d0, d1 = uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]
    uv_area = d0[:, 0] * d1[:, 1] - d0[:, 1] * d1[:, 0]
    assert (np.abs(uv_area) > 1e-10).all(), (lod, int((abs(uv_area) < 1e-10).sum()))
    report.append(dict(lod=lod, triangles=len(faces), valid_geometry=True, valid_uvs=True))
normal = np.asarray(Image.open(ROOT / "Assets/materials/riverside/crate_v2/crate_normal.png"), float) / 127.5 - 1
assert np.allclose(np.linalg.norm(normal, axis=-1), 1, atol=.015)
assert normal[:, :, 2].min() > 0
result = dict(lods=report, normal_map_valid=True, live_pad_unchanged=True, live_scene_unchanged=True)
(OUT / "verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
