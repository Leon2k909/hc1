"""Check the saved hose installation and render it without changing the active scene. Editor must be open."""
import ast
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from native import Editor

ROOT = Path(__file__).absolute().parents[3]
WORK = ROOT / 'output/asset-improvement-20261030/spillway-hose'
MODEL = 'models/maps/spillway/hose_coil_v2/hose_coil.vmdl'

before = json.loads((WORK / 'retired/spillway.scene').read_text())
after = json.loads((ROOT / 'Assets/scenes/maps/spillway/spillway.scene').read_text())
root = next(o for o in after['GameObjects'] if o.get('Name') == 'Spillway')
covers = [o for o in root['Children'] if o.get('Name') == 'Yard Hose']
assert len(covers) == 1 and covers[0]['Position'] == '-1080,-90,0'
assert [c['__type'] for c in covers[0]['Components']] == ['Sandbox.ModelRenderer']
root['Children'].remove(covers[0])
assert before == after, 'Scene changed beyond the hose'
retired = (WORK / 'retired/spillway_cargo.obj').read_bytes().decode()
v, kept, removed, current = [], [], [], None
for line in retired.split('\n'):
    if line.startswith('v '):
        v.append(tuple(map(float, line.split()[1:4])))
    elif line.startswith('usemtl'):
        current = line.split()[1]
    elif line.startswith('f ') and current == 'rv_dark':
        points = [v[int(token.split('/')[0]) - 1] for token in line.split()[1:]]
        if all(-144 <= x <= -36 and 1.7 <= z <= 6.3 and -1108 <= n <= -1052 for x, z, n in points):
            removed.append(line)
            continue
    kept.append(line)
assert len(removed) == 930
assert '\n'.join(kept).encode() == (ROOT / 'Assets/models/maps/spillway/spillway_cargo.obj').read_bytes()
ast.parse((ROOT / 'Tools/spillway_map.py').read_text())
(WORK / 'installed').mkdir(exist_ok=True)
(WORK / 'installed/static-validation.json').write_text(json.dumps(dict(RemovedFaces=930, SceneOnlyAddedHose=True,
    ColliderAdded=False, GeneratorSyntax='passed'), indent=2))
print('Static checks passed: exactly 930 faces removed; scene only adds one renderer; generator parses.', flush=True)
if '--static' in sys.argv:
    sys.exit(0)
with Editor() as editor:
    print(json.dumps(editor.call('editor_status')), flush=True)
    print(json.dumps(editor.call('asset_compile', dict(path='models/maps/spillway/spillway_cargo.vmdl'))), flush=True)
    template = (ROOT / 'Sources/Spillway/cargo-props-v2/candidates.cs.txt').read_text()
    shots = ', '.join([
        '("standing", new Vector3(-950f,-130f,70f), new Vector3(-1080f,-90f,3f),55f)',
        '("low", new Vector3(-1014f,-114f,19f), new Vector3(-1080f,-90f,2.5f),58f)'])
    code = template.replace('%OUT%', 'output/asset-improvement-20261030/spillway-hose/installed').replace('%SHOTS%', shots)
    old_return = 'return new { Written = shots.Length, Renderers = scene.GetAllComponents<ModelRenderer>().Count() };'
    replacement = '''var hoses = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath == "models/maps/spillway/hose_coil_v2/hose_coil.vmdl").ToArray();
    var rays = new System.Collections.Generic.List<object>();
    using (scene.Push())
    {
        foreach (var p in new[] { new Vector3(-1080,-90,50), new Vector3(-1093,-46,50), new Vector3(-1070,-130,50) })
        {
            var hit = scene.Trace.Ray(p, p.WithZ(-10)).Run();
            if (!hit.Hit || Math.Abs(hit.EndPosition.z) > .1f) throw new InvalidOperationException("Hose-area floor collision changed.");
            rays.Add(new { At = p, Hit = hit.GameObject?.Name, Height = hit.EndPosition.z });
        }
    }
    if (hoses.Length != 1 || hoses[0].Model.IsError || hoses[0].GameObject.Components.Get<ModelCollider>() is not null)
        throw new InvalidOperationException("Expected one valid visual-only hose.");
    return new { Hoses = hoses.Length, HoseCollider = false, Rays = rays, Written = shots.Length,
        Errors = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is null || r.Model.IsError).Select(r => r.GameObject.Name).ToArray() };'''
    assert code.count(old_return) == 1
    result = editor.script(code.replace(old_return, replacement), 'installed-hose.cs')
    print(json.dumps(result, indent=2), flush=True)
    (WORK / 'installed/native-validation.json').write_text(json.dumps(result, indent=2))
