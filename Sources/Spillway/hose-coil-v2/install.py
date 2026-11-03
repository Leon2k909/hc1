"""Guarded offline installation. python install.py [--apply]. Refuses to write while an editor is connected.

Keeps every other OBJ line and every scene object. Backups go into this candidate's retired directory.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).absolute().parents[3]
WORK = ROOT / 'output/asset-improvement-20261030/spillway-hose'
MODEL = 'models/maps/spillway/hose_coil_v2/hose_coil.vmdl'
mesh = ROOT / 'Assets/models/maps/spillway/spillway_cargo.obj'
scene = ROOT / 'Assets/scenes/maps/spillway/spillway.scene'
generator = ROOT / 'Tools/spillway_map.py'
manifest = json.loads((WORK / 'review_manifest.json').read_text())
for path, expected in manifest['unchanged'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Changed since review: ' + path
raw = mesh.read_bytes().decode('utf-8')
vertices, keep, removed = [], [], []
material = None
for line in raw.split('\n'):
    if line.startswith('v '):
        vertices.append(tuple(map(float, line.split()[1:4])))
    elif line.startswith('usemtl'):
        material = line.split()[1]
    elif line.startswith('f ') and material == 'rv_dark':
        corners = [vertices[int(token.split('/')[0]) - 1] for token in line.split()[1:]]
        if all(-144 <= x <= -36 and 1.7 <= z <= 6.3 and -1108 <= n <= -1052 for x, z, n in corners):
            removed.append(line)
            continue
    keep.append(line)
assert len(removed) == 930, len(removed)
text = scene.read_text(encoding='utf-8')
data = json.loads(text)
assert MODEL not in text
root = next(item for item in data['GameObjects'] if item.get('Name') == 'Spillway')
cover = copy.deepcopy(next(item for item in root['Children'] if item.get('Name') == 'B2 Canvas Cover'))
guid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'hc1/spillway/hose-coil/' + name))
cover.update(__guid=guid('object'), Name='Yard Hose', Position='-1080,-90,0', Rotation='0,0,0,1')
assert [c['__type'] for c in cover['Components']] == ['Sandbox.ModelRenderer']
meta = json.loads((ROOT / 'Assets' / (MODEL + '.meta')).read_text())
cover['Components'][0].update(__guid=guid('renderer'), Model={'Id': meta['guid'], 'Path': MODEL})
root['Children'].append(cover)
new_scene = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
assert json.dumps(json.loads(text), indent=2, ensure_ascii=False) + '\n' == text, 'Unexpected scene serialization'
gen = generator.read_bytes().decode('utf-8')
newline = '\r\n' if '\r\n' in gen else '\n'
old = '\n'.join(['    for j in range(3):',
    '        pts=[(90+math.cos(t)*(44+j*4),-1080+math.sin(t)*(22+j*2),3+j) for t in np.linspace(0,2*math.pi,32)]',
    '        for a,b in zip(pts[:-1],pts[1:]):P.rod(m,a,b,1.2,"rv_dark",5)']).replace('\n', newline)
assert gen.count(old) == 1
gen = gen.replace(old, '    # The continuous yard hose is a separate visual model, placed by scene(): Sources/Spillway/hose-coil-v2.')
anchor = '            # The B2 deck\'s canvas cover: drawn only, as its collision box is in the east model.'
assert gen.count(anchor) == 1
addition = '\n'.join(['            hose="models/maps/spillway/hose_coil_v2/hose_coil.vmdl"',
    '            root["Children"].append(K.game_object(IDS,"Yard Hose","cargo/hose",K.to_world((90,-1080,0)),"0,0,0,1",components=[',
    '                K.component(IDS,"Sandbox.ModelRenderer","cargo/hose/renderer",Model=hose,RenderType="On",Tint="1,1,1,1")]))', '']).replace('\n', newline)
gen = gen.replace(anchor, addition + anchor)
import ast
ast.parse(gen)
print('Remove exactly 930 hose faces, add one renderer without a collider, retain it in the generator.')
if '--apply' not in sys.argv:
    print('Dry run: nothing written.')
    sys.exit(0)
engine = os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
instances = json.loads(subprocess.check_output([str(Path(engine) / 'bin/managed/sbox-cli.exe'), '--list'], cwd=ROOT, text=True))
assert not instances, 'Editor is now open: use native scene tools instead of offline installation.'
retired = WORK / 'retired'
retired.mkdir(exist_ok=True)
for path in (mesh, scene, generator):
    target = retired / path.name
    assert not target.exists(), 'Backup already exists; inspect installation instead of retrying.'
    shutil.copy2(path, target)
for path, content in [(mesh, '\n'.join(keep)), (scene, new_scene), (generator, gen)]:
    incoming = path.with_name(path.name + '.hose-incoming')
    incoming.write_bytes(content.encode('utf-8'))
    os.replace(incoming, path)
print('Installed. Native validation pending editor availability.')
