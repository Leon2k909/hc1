"""Check closed geometry, bounds and atlas sampling for the offline prop trial."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import belltower_firewood_trial as T
from map_kit import Model

atlas = np.asarray(Image.open(T.GENERATED / 'firewood-cuts-v1.png').getchannel('A'))
regions = T.atlas_regions()
results = []
before_rng = np.random.get_state()
for box in ((-50, 50, -15, 15, 0), (-1840, -1740, -1170, -1140, -48)):
    model = Model()
    records = T.woodpile(model, *box, regions=regions)
    edges = Counter()
    volume = 0.0
    vertices = []
    min_alpha = 255
    normal_alignment = 1.0
    for paint, faces in model.polygons.items():
        for index, (points, normal) in enumerate(faces):
            vertices.extend(points)
            keys = [tuple(np.round(p, 6)) for p in points]
            for a, b in zip(keys, keys[1:] + keys[:1]):
                edges[tuple(sorted((a, b)))] += 1
            for k in range(1, len(points) - 1):
                volume += np.dot(points[0], np.cross(points[k], points[k + 1])) / 6
            normals = model.polygon_normals.get((paint, index), [normal])
            normal_alignment = min(normal_alignment, *(float(np.dot(n, normal)) for n in normals))
            if paint == T.CUT:
                uv = np.asarray(model.polygon_uvs[(paint, index)])
                centre = uv.mean(axis=0)
                # Triangle interiors, edges and vertices all remain in opaque wood.
                samples = np.vstack([centre + (uv - centre) * fraction for fraction in np.linspace(0, 1, 11)])
                x = np.rint(samples[:, 0] * atlas.shape[1]).astype(int)
                y = np.rint((1 - samples[:, 1]) * atlas.shape[0]).astype(int)
                assert np.all((x >= 0) & (x < atlas.shape[1]) & (y >= 0) & (y < atlas.shape[0]))
                min_alpha = min(min_alpha, int(atlas[y, x].min()))
    points = np.asarray(vertices)
    assert np.isfinite(points).all()
    assert all(count == 2 for count in edges.values()), 'Open or non-manifold surface'
    assert volume > 0 and normal_alignment > .95
    assert min_alpha >= 250, 'Cut-face UV crosses the transparent atlas padding'
    e0, e1, n0, n1, z = box
    assert np.all(points.min(axis=0) >= (e0 - .001, n0 - .001, z - .001))
    assert np.all(points.max(axis=0) <= (e1 + .001, n1 + .001, z + 40.001))
    assert not model.boxes and not model.hulls
    results.append({'placement': box, 'logs': len(records), 'triangles': model.triangle_count(),
                    'closed_edges': len(edges), 'outward_volume': volume,
                    'minimum_normal_alignment': normal_alignment, 'minimum_sampled_alpha': min_alpha,
                    'bounds': [points.min(axis=0).tolist(), points.max(axis=0).tolist()]})
after_rng = np.random.get_state()
assert before_rng[0] == after_rng[0] and np.array_equal(before_rng[1], after_rng[1]) and before_rng[2:] == after_rng[2:]
manifest = json.loads((T.OUT / 'trial.json').read_text(encoding='utf-8'))
for path, expected in manifest['source_sha256'].items():
    assert T.digest(ROOT / path) == expected, path
result = {'passed': True, 'placements': results, 'original_albedos_unchanged': True,
          'shared_random_state_preserved': True, 'production_generator_unchanged': True,
          'native_verified': False, 'trial_sha256': T.digest(T.OUT / 'trial.json')}
(T.OUT / 'geometry-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
