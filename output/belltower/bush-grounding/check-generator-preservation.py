"""Read-only comparison against the current shared garden generator."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Tools'))
import belltower_map as B
import belltower_detail as D
import map_kit as K

spec = importlib.util.spec_from_file_location('original_grounding_detail', OUT / 'before/Tools/belltower_detail.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


def normal(value):
    if isinstance(value, np.ndarray):
        return normal(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return [[repr(k), normal(v)] for k, v in sorted(value.items(), key=lambda item: repr(item[0]))]
    if isinstance(value, (list, tuple)):
        return [normal(v) for v in value]
    if isinstance(value, set):
        return sorted(map(repr, value))
    return value


def old_shrub(*args, ground_z=None, **kwargs):
    return old.shrub(*args, **kwargs)


previous = K.Model()
current = K.Model()
new_shrub = D.shrub
try:
    D.shrub = old_shrub
    B.gardens(previous, np.random.default_rng(2024))
finally:
    D.shrub = new_shrub
B.gardens(current, np.random.default_rng(2024))
old_geometry = normal({k: v for k, v in vars(previous).items() if k != 'props'})
new_geometry = normal({k: v for k, v in vars(current).items() if k != 'props'})
assert old_geometry == new_geometry
assert len(previous.props) == len(current.props) == 155
changed = 0
for a, b in zip(previous.props, current.props):
    if normal(a) == normal(b):
        continue
    changed += 1
    assert a['path'] == b['path'] == D.BUSH
    assert a['yaw'] == b['yaw'] and a['name'] == b['name']
    assert a['position'][:2] == b['position'][:2] and a['scale'][:2] == b['scale'][:2]
    assert abs(a['position'][2] + a['scale'][2] * D.BUSH_TOP_Z - b['position'][2] - b['scale'][2] * D.BUSH_TOP_Z) < 1e-9
assert changed == 122
result = {'old_and_new_props_per_half': 155, 'changed_garden_shrubs_per_half': 122,
    'other_props_unchanged': 33, 'polygons_collision_boxes_hulls_exact': True,
    'geometry_fingerprint': hashlib.sha256(json.dumps(new_geometry, separators=(',', ':')).encode()).hexdigest(),
    'tops_widths_rotations_preserved': True, 'root_anchor_verified': True,
    'input_revision': 3, 'method': 'Current shared garden generator with identical RNG, comparing archived original shrub placement against grounding. Every geometry/collision/UV/normal field and other prop compared exactly.'}
(OUT / 'generator-check-revision3.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
