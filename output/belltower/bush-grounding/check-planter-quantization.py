from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tools'))
import belltower_planters as P
import map_kit as K

spec = importlib.util.spec_from_file_location('planters_before_quantization_fix', OUT / 'planter-generator-before-zero-area-fix.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
before = K.Model()
after = K.Model()
for centre in P.CENTRES:
    seed = abs(int(centre[0] * 7 + centre[1]))
    old.build(before, centre, seed=seed)
    P.build(after, centre, seed=seed)


def faces(model):
    kept = []
    dropped = []
    for paint, polygons in model.polygons.items():
        for i, (points, normal) in enumerate(polygons):
            row = {'paint': paint, 'points': [p.tolist() for p in points], 'normal': normal.tolist(),
                'uv': model.polygon_uvs.get((paint, i)),
                'normals': [n.tolist() for n in model.polygon_normals[(paint, i)]] if (paint, i) in model.polygon_normals else None}
            exported = np.array([list(map(float, K.obj_vector(K.to_world(p)).split())) for p in points])
            zero = len(points) == 3 and not np.any(np.cross(exported[1] - exported[0], exported[2] - exported[0]))
            (dropped if zero else kept).append(json.dumps(row, sort_keys=True))
    return kept, dropped


old_kept, old_zero = faces(before)
new_kept, new_zero = faces(after)
assert Counter(old_kept) == Counter(new_kept)
assert len(old_zero) == 6 and not new_zero
assert before.boxes == after.boxes and before.hulls == after.hulls and before.props == after.props
assert before.material_overrides == after.material_overrides and before.tile_overrides == after.tile_overrides
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
result = {'generator_before_sha256': sha(OUT / 'planter-generator-before-zero-area-fix.py'),
    'generator_after_sha256': sha(ROOT / 'Tools/belltower_planters.py'),
    'invisible_collapsed_triangles_removed_per_half': 6, 'all_other_positions_uvs_normals_exact': True,
    'materials_collision_and_other_props_exact': True, 'new_zero_area_triangles': 0,
    'method': 'Rebuild all three original planter placements with identical seeds; compare every surviving polygon and attribute after checking OBJ export precision.'}
(OUT / 'planter-quantization-check.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
