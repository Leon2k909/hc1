"""Cut temporary review copies of the first west wall vent; never writes the map's source model or scene."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).absolute().parents[3]
WORK = ROOT / 'output/asset-improvement-20261030/spillway-vent'
OUT = ROOT / 'Assets/models/compare_old/spillway_vent_v2'
OUT.mkdir(parents=True, exist_ok=True)
doc = (ROOT / 'Assets/models/maps/spillway/spillway_west.vmdl').read_text()
REMAP = {a.removesuffix('.vmat'): b for a, b in re.findall(r'from = "([^"]+)" to = "([^"]+)"', doc)}
v, vt, vn = [], [], []
all_faces, old, rest = [], [], []
current = None
for line in (ROOT / 'Assets/models/maps/spillway/spillway_west.obj').read_text().splitlines(keepends=True):
    if line.startswith('v '):
        v.append([float(x) for x in line.split()[1:4]] + [line])
    elif line.startswith('vt '):
        vt.append(line)
    elif line.startswith('vn '):
        vn.append(line)
    elif line.startswith('usemtl'):
        current = line.split()[1]
    elif line.startswith('f '):
        corners = [tuple(int(x) for x in t.split('/')) for t in line.split()[1:]]
        face = (current, corners)
        all_faces.append(face)
        inside = all(1301 <= v[c[0] - 1][0] <= 1329 and 24 <= v[c[0] - 1][1] <= 120
                     and 169 <= v[c[0] - 1][2] <= 271 for c in corners)
        if inside:
            old.append(face)
assert old, 'No vent faces found'
materials = {m for m, _ in old}
assert materials <= {'rv_steel', 'rv_frame', 'rv_louvre', 'rv_black'}, materials
old_keys = {tuple(c) for _, c in old}
rest = [(m, c) for m, c in all_faces if m in materials and tuple(c) not in old_keys]
template = (ROOT / 'Sources/Spillway/canvas-cover-v2/cut_old.py').read_text()
template = template.replace('filename = "models/compare_old/{name}.obj"', 'filename = "models/compare_old/spillway_vent_v2/{name}.obj"')
function = next(node for node in ast.parse(template).body if isinstance(node, ast.FunctionDef) and node.name == 'write')
exec(compile(ast.Module(body=[function], type_ignores=[]), '<shared-obj-extractor>', 'exec'))
write('old_vent', old)
write('west_rest', rest)
manifest = dict(old_triangles=len(old), remaining_triangles=len(rest), hidden_materials=sorted(materials),
    unchanged={path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in
               ['Assets/models/maps/spillway/spillway_west.obj', 'Assets/scenes/maps/spillway/spillway.scene', 'Tools/spillway_map.py']})
WORK.mkdir(exist_ok=True)
(WORK / 'review_manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
