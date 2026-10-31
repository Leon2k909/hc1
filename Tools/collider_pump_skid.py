"""Exact pump-skid geometry and finish approved in the offline model review."""
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = 'models/props/collider/pump-skid-trial-v1/after.obj'
MATERIAL_DIR = 'materials/collider/pump-skid-trial-v1'
ORIGIN = np.array((-850., -350., 0.))


@lru_cache(maxsize=1)
def mesh():
    positions, uv, normals, faces = [], [], [], []
    paint = ''
    for line in (ROOT / 'Assets' / RESOURCE).read_text().splitlines():
        if line.startswith('v '):
            a, z, n = map(float, line.split()[1:])
            positions.append(np.array((-a, n, z)))
        elif line.startswith('vt '):
            uv.append(tuple(map(float, line.split()[1:])))
        elif line.startswith('vn '):
            a, z, n = map(float, line.split()[1:])
            normals.append(np.array((-a, n, z)))
        elif line.startswith('usemtl '):
            paint = line[7:]
        elif line.startswith('f '):
            ids = [[int(v) - 1 for v in token.split('/')] for token in line.split()[1:]]
            faces.append((paint, [positions[v] for v, t, n in ids],
                          [uv[t] for v, t, n in ids], [normals[n] for v, t, n in ids]))
    return faces


def append(model):
    for paint, points, uv, normals in mesh():
        model.polygon(paint, [ORIGIN + p for p in points], uv=uv, normals=normals)
