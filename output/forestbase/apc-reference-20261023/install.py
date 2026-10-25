"""Install only the FB/041 source replacement; no editor interaction."""
from pathlib import Path
import os, json, hashlib, shutil, re, py_compile

r = Path('C:/Users/mimi-/Documents/S&box Projects/hc1')
out = Path(__file__).parent
dest = r / 'Assets/models/maps/forestbase'
mat = r / 'Assets/materials/forestbase/apc'
audit = json.loads((out / 'audit.json').read_text())
owned = {'armor', 'metal', 'rubber', 'stencil', 'amber', 'red'}
sources = [p for p in (out / 'materials').iterdir()
           if p.suffix in {'.png', '.vmat'} and p.stem.split('_')[0] in owned]
assert (out / 'apc-preview.png').exists()
for ext in ('.obj', '.mtl', '.vmdl'):
    assert (dest / ('yard' + ext)).read_bytes() == (out / ('yard.before' + ext)).read_bytes(), 'Concurrent yard change: ' + ext
for ext in ('.mtl', '.vmdl'):
    assert (out / ('yard' + ext)).read_bytes() == (out / ('yard.before' + ext)).read_bytes()
for p in (out / 'materials-before').iterdir():
    if p.is_file():
        assert (mat / p.name).read_bytes() == p.read_bytes(), 'Concurrent material change: ' + p.name
for p in sources:
    if p.suffix == '.vmat':
        for ref in re.findall(r'"(materials/forestbase/apc/[^\"]+\.png)"', p.read_text()):
            assert (out / 'materials' / Path(ref).name).exists(), ref
py_compile.compile(str(r / 'Tools/forestbase_apc.py'), doraise=True)

def put(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.apc-pending')
    shutil.copy2(source, temporary)
    os.replace(temporary, target)
    assert target.read_bytes() == source.read_bytes()

for p in sources:
    put(p, mat / p.name)
put(out / 'yard.obj', dest / 'yard.obj')
layout = r / 'output/forestbase/layout.json'
if layout.exists():
    shutil.copy2(layout, out / 'layout.before.json')
    data = json.loads(layout.read_text())
    data['stats']['yard']['triangles'] = audit['trianglesAfter']
    layout.write_text(json.dumps(data, indent=2))
for ext in ('.mtl', '.vmdl'):
    assert (dest / ('yard' + ext)).read_bytes() == (out / ('yard.before' + ext)).read_bytes()
installed = [dest / 'yard.obj', dest / 'yard.vmdl', r / 'Tools/forestbase_apc.py'] + [mat / p.name for p in sources]
integration = {
    'editorUsed': False,
    'engineCompileVerified': False,
    'offlinePreview': 'apc-preview.png',
    'allNonAPCFacesUnchanged': True,
    'modelDocAndPhysicsUnchanged': True,
    'latestTruckRevisionPreserved': True,
    'audit': audit,
    'installed': {str(p.relative_to(r)): hashlib.sha256(p.read_bytes()).hexdigest() for p in installed}
}
(out / 'integration.json').write_text(json.dumps(integration, indent=2))
print(json.dumps({'installedMaterialFiles': len(sources), 'yardTriangles': audit['trianglesAfter'], 'editorUsed': False, 'engineCompileVerified': False}, indent=2))
