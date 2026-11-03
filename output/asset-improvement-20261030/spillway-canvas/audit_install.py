import ast
import json
from pathlib import Path

root = Path.cwd()
work = root / 'output/asset-improvement-20261030/spillway-canvas'
old = (work / 'retired/spillway_east.obj').read_bytes().decode('utf-8')
vertices, kept = [], []
material = None
counts = {'sw_tarp': 0, 'straps': 0}
for line in old.split('\n'):
    if line.startswith('v '):
        vertices.append(tuple(map(float, line.split()[1:4])))
    elif line.startswith('usemtl'):
        material = line.split()[1]
        if material == 'sw_tarp':
            continue
    elif line.startswith('f '):
        if material == 'sw_tarp':
            counts['sw_tarp'] += 1
            continue
        corners = [vertices[int(token.split('/')[0]) - 1] for token in line.split()[1:]]
        if material == 'rv_dark' and all(-1603 <= x <= -1497 and 127.9 <= z <= 220.1 and -1772.1 <= n <= -1638.9 for x, z, n in corners):
            counts['straps'] += 1
            continue
    kept.append(line)
assert counts == {'sw_tarp': 11520, 'straps': 48}, counts
assert '\n'.join(kept).encode('utf-8') == (root / 'Assets/models/maps/spillway/spillway_east.obj').read_bytes(), 'Unexpected east-model changes after backup'
before = json.loads((work / 'retired/spillway.scene').read_text(encoding='utf-8'))
after = json.loads((root / 'Assets/scenes/maps/spillway/spillway.scene').read_text(encoding='utf-8'))
spillway = next(o for o in after['GameObjects'] if o.get('Name') == 'Spillway')
covers = [o for o in spillway['Children'] if o.get('Name') == 'B2 Canvas Cover']
assert len(covers) == 1
assert covers[0]['Position'] == '-1705,-1550,128'
assert [c['__type'] for c in covers[0]['Components']] == ['Sandbox.ModelRenderer']
spillway['Children'].remove(covers[0])
assert before == after, 'Unexpected scene changes after backup'
for file in [root / 'Tools/spillway_map.py', *list((root / 'Sources/Spillway/canvas-cover-v2').glob('*.py'))]:
    ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
report = dict(RemovedFaces=counts, EastModelOnlyExpectedCuts=True, SceneOnlyAddedCover=True, PythonSyntax='passed')
(work / 'installed/static-validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
