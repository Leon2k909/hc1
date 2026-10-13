import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'Tools'))
import railhead_station as S

planes = defaultdict(list)
for name, model in S.build().items():
    for paint, polygons in model.polygons.items():
        if paint not in ('rw_sandstone', 'rw_dressed', 'rw_dressed_red'):
            continue
        for index, (points, normal) in enumerate(polygons):
            p = np.asarray(points)
            axis = int(np.argmax(abs(normal)))
            if abs(normal[axis]) < .9999 or len(points) != 4:
                continue
            other = [a for a in range(3) if a != axis]
            # Four axis-aligned corners, not the arch's trapezoidal head.
            if any(len(set(np.round(p[:, a], 4))) != 2 for a in other):
                continue
            key = (axis, round(p[0, axis], 3), int(np.sign(normal[axis])))
            planes[key].append((name, paint, index, p[:, other].min(0), p[:, other].max(0)))

count = 0
for plane, faces in planes.items():
    for i, a in enumerate(faces):
        for b in faces[i + 1:]:
            overlap = np.minimum(a[4], b[4]) - np.maximum(a[3], b[3])
            if np.all(overlap > .01):
                count += 1
                print('OVERLAP', plane, a[:3], b[:3], 'area', overlap.prod())
print('Masonry rectangle overlaps:', count)
