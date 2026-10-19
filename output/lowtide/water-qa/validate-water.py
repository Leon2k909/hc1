"""Validate Lowtide's scope, wave-normal assets and stitched shore geometry."""
from pathlib import Path
import hashlib
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_map as L

files = sorted((ROOT / "Assets/materials/lowtide/sea").glob("lt_ocean_*_normal.png"))
assert len(files) == 2
checksums = []
for path in files:
    with Image.open(path) as tex:
        assert tex.size == (1024, 1024) and tex.mode == "RGB", (path, tex.size, tex.mode)
        values = np.asarray(tex, np.int16)
        assert 130 < float(np.mean(values[:, :, 2])) < 255
        assert float(np.std(values[:, :, 0])) > 10
        interior = (np.abs(np.diff(values[:, :, 0], axis=1)).mean() +
                    np.abs(np.diff(values[:, :, 1], axis=0)).mean()) * .5
        seams = (np.abs(values[:, 0] - values[:, -1]).mean() +
                 np.abs(values[0] - values[-1]).mean()) * .5
        assert seams < interior * 2.5, (path, seams, interior)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksums.append(digest)
    print(f"{path.name}: 1024² RGB, {path.stat().st_size:,} bytes, sha256={digest[:20]}, seam={seams:.2f}, neighbours={interior:.2f}")
assert checksums[0] != checksums[1]

surfaces = L.water_model().polygons["lt_water"]
canal, *ocean = (polygon[0] for polygon in surfaces[:4])
assert len(surfaces) == 48
assert all(abs(vertex[2] - L.WATER_Z) < 1e-6 for polygon in [canal, *ocean] for vertex in polygon)
assert all(polygon[2][1] == L.MOUTH_N for polygon in ocean)
assert canal[0][1] == L.MOUTH_N
assert ocean[0][1][0] == ocean[1][0][0] == -128
assert ocean[1][1][0] == ocean[2][0][0] == 128
assert canal[0][0] == -128 and canal[1][0] == 128
print(f"model: flat canal/sea at z={L.WATER_Z}, common northing={L.MOUTH_N}; no connecting ramp")
