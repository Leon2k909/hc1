"""Extract only the old hose and the remaining cargo rv_dark faces for reversible comparisons.

The saved map and its models are never written. These temporary models can be archived after approval.
"""
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).absolute().parents[3]
WORK = ROOT / 'output/asset-improvement-20261030/spillway-hose'
OUT = ROOT / 'Assets/models/compare_old/spillway_hose_v2'
OUT.mkdir(parents=True, exist_ok=True)
REMAP = {'rv_dark': 'materials/riverdale/rv_dark.vmat'}
v, vt, vn, old, rest = [], [], [], [], []
current = None
source = ROOT / 'Assets/models/maps/spillway/spillway_cargo.obj'
for line in source.read_text().splitlines(keepends=True):
    if line.startswith('v '):
        v.append([float(x) for x in line.split()[1:4]] + [line])
    elif line.startswith('vt '):
        vt.append(line)
    elif line.startswith('vn '):
        vn.append(line)
    elif line.startswith('usemtl'):
        current = line.split()[1]
    elif line.startswith('f ') and current == 'rv_dark':
        corners = [tuple(int(x) for x in token.split('/')) for token in line.split()[1:]]
        # OBJ coordinates (-e, z, n), with generous limits around the three original rings only.
        inside = all(-144 <= v[c[0] - 1][0] <= -36 and 1.7 <= v[c[0] - 1][1] <= 6.3
                     and -1108 <= v[c[0] - 1][2] <= -1052 for c in corners)
        (old if inside else rest).append((current, corners))
assert len(old) == 930, f'Expected 3 x 31 rods x 5 sides x 2 triangles; found {len(old)}'

# The existing map-extraction writer preserves OBJ positions, normals, UVs and ModelDoc conventions.
template = (ROOT / 'Sources/Spillway/canvas-cover-v2/cut_old.py').read_text()
template = template.replace('filename = "models/compare_old/{name}.obj"', 'filename = "models/compare_old/spillway_hose_v2/{name}.obj"')
function = next(node for node in ast.parse(template).body if isinstance(node, ast.FunctionDef) and node.name == 'write')
exec(compile(ast.Module(body=[function], type_ignores=[]), '<shared-obj-extractor>', 'exec'))
write('old_hose', old)
write('cargo_dark_rest', rest)
manifest = dict(old_triangles=len(old), other_dark_triangles=len(rest),
                unchanged={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                           ['Assets/models/maps/spillway/spillway_cargo.obj', 'Assets/scenes/maps/spillway/spillway.scene', 'Tools/spillway_map.py']})
WORK.mkdir(parents=True, exist_ok=True)
(WORK / 'review_manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
