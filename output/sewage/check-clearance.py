"""Conservative stair headroom check; supplements, does not replace, engine navmesh QA."""
import os
import platform
import sys
import json
from pathlib import Path

platform.machine = lambda: os.environ.get('PROCESSOR_ARCHITECTURE', 'AMD64')
os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
import numpy as np
from scipy.spatial import ConvexHull
import sewage_map as S

models = S.build()
solids = []
for group, model in models.items():
    if group in ('water', 'cascades', 'signage'):
        continue
    for index, (center, axes, size, surface) in enumerate(model.boxes):
        center, axes, size = np.asarray(center), np.asarray(axes), np.asarray(size)
        normals = np.vstack((axes, -axes))
        offsets = -normals @ center - np.tile(size / 2, 2)
        top = center[2] + np.sum(np.abs(axes[:, 2]) * size / 2)
        solids.append((f'{group}/box/{index}', np.column_stack((normals, offsets)), top))
    for index, (points, surface) in enumerate(model.hulls):
        points = np.asarray(points)
        solids.append((f'{group}/hull/{index}', ConvexHull(points).equations, points[:, 2].max()))

def intersects_body(feet, equations, radius=16):
    # Capsule axis, with two units above the sampled support surface.
    p0 = feet + np.array((0, 0, 18))
    p1 = feet + np.array((0, 0, 58))
    base = equations[:, :3] @ p0 + equations[:, 3] - radius
    slope = equations[:, :3] @ (p1 - p0)
    flat = np.abs(slope) < 1e-8
    if np.any(base[flat] > 0):
        return False
    lo, hi = 0.0, 1.0
    for b, v in zip(base[~flat], slope[~flat]):
        if v > 0:
            hi = min(hi, -b / v)
        else:
            lo = max(lo, -b / v)
    return lo <= hi

results = []
for index, (points, surface) in enumerate(models['catwalks'].hulls):
    points = np.asarray(points)
    start, end = points[4:6].mean(axis=0), points[6:8].mean(axis=0)
    width = abs(points[5, 0] - points[4, 0])
    blocked = []
    for across in (0, -width / 2 + 28, width / 2 - 28):
        for t in np.linspace(.03, .97, 25):
            feet = start + (end - start) * t + np.array((across, 0, 0))
            for name, equations, top in solids:
                if name == f'catwalks/hull/{index}' or top <= feet[2] + 18:
                    continue
                if intersects_body(feet, equations):
                    blocked.append({'t': round(float(t), 3), 'across': round(float(across), 1),
                                    'position': feet.round(1).tolist(), 'obstacle': name})
    results.append({'stair': index, 'start': start.tolist(), 'end': end.tolist(),
                    'obstacles': sorted(set(p['obstacle'] for p in blocked)), 'hits': blocked})
report = {'method': 'conservative capsule against expanded convex solids; native route checks still required',
          'stairs': results}
(ROOT / 'output/sewage/clearance-report.json').write_text(json.dumps(report, indent=2))
print(json.dumps([{'stair': p['stair'], 'start': p['start'], 'end': p['end'],
                   'obstacles': p['obstacles'], 'hits': len(p['hits'])} for p in results], indent=2))
