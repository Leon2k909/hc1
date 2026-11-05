"""Native installation of the approved first wall vent. python install.py inspect|prepare|apply|validate|archive.

Staging preserves current scene and generator edits. Mutations run through the editor; keep collision hulls intact.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Sources/Spillway/hose-coil-v2'))
from native import Editor

WORK = ROOT / 'output/asset-improvement-20261030/spillway-vent'
MODEL = 'models/maps/spillway/wall_vent_v2/wall_vent.vmdl'
MODE = sys.argv[1]
if MODE == 'inspect':
    with Editor() as editor:
        print(json.dumps(editor.script('''return new { Game.IsPlaying, Active = Editor.SceneEditorSession.Active?.Scene.Name,
Sessions = Editor.SceneEditorSession.All.Select(s => new { s.Scene.Name, Path = s.Scene.Source?.ResourcePath, s.HasUnsavedChanges }).ToArray() };'''), indent=2))
        catalog = editor.call('search_tools', dict(query='save scene'))
        print(json.dumps([t for t in catalog['tools'] if t['name'] in ('save_scene','list_scenes')], indent=2))
elif MODE == 'prepare':
    mesh = ROOT / 'Assets/models/maps/spillway/spillway_west.obj'
    scene = ROOT / 'Assets/scenes/maps/spillway/spillway.scene'
    generator = ROOT / 'Tools/spillway_map.py'
    review = json.loads((WORK / 'review_manifest.json').read_text())
    for path in (mesh, scene):
        relative = path.relative_to(ROOT).as_posix()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == review['unchanged'][relative], 'Saved review input changed: ' + relative
    raw = mesh.read_bytes().decode('utf-8')
    verts, keep, removed, material = [], [], [], None
    for line in raw.split('\n'):
        if line.startswith('v '):
            verts.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith('usemtl'):
            material = line.split()[1]
        elif line.startswith('f '):
            corners = [verts[int(t.split('/')[0])-1] for t in line.split()[1:]]
            if all(1301 <= x <= 1329 and 24 <= z <= 120 and 169 <= n <= 271 for x,z,n in corners):
                assert material in {'rv_steel','rv_black','rv_frame','rv_louvre'}
                removed.append(line)
                continue
        keep.append(line)
    assert len(removed) == 386, len(removed)
    data = json.loads(scene.read_text(encoding='utf-8'))
    assert MODEL not in json.dumps(data), 'Vent already installed; inspect it instead of retrying.'
    root = next(g for g in data['GameObjects'] if g.get('Name') == 'Spillway')
    template = next(c for c in root['Children'] if c.get('Name') == 'B2 Canvas Cover')
    new = json.loads(json.dumps(template))
    guid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'hc1/spillway/wall-vent/' + name))
    new.update(__guid=guid('object1'), Name='Turbine Wall Vent 1', Position='220,1328,25', Rotation='0,0,0,1')
    assert [c['__type'] for c in new['Components']] == ['Sandbox.ModelRenderer']
    meta = json.loads((ROOT / 'Assets' / (MODEL + '.meta')).read_text())
    new['Components'][0].update(__guid=guid('renderer1'), Model={'Id':meta['guid'], 'Path':MODEL})
    root['Children'].append(new)
    source = generator.read_bytes().decode('utf-8')
    nl = '\r\n' if '\r\n' in source else '\n'
    old = nl.join(['    for n in (220,1150):',
        '        box(m,-1328,-1310,n-50,n+50,25,118,"rv_steel",METAL)',
        '        P.louvre(m,(-1308,n,75),(0,1,0),86,64)'])
    replacement = nl.join(['    # The first wall vent is a separate visual model; retain both original collision boxes.',
        '    for n in (220,1150):',
        '        box(m,-1328,-1310,n-50,n+50,25,118,{"default":None} if n==220 else "rv_steel",METAL)',
        '        if n!=220:P.louvre(m,(-1308,n,75),(0,1,0),86,64)'])
    assert source.count(old) == 1, 'West vent generator block changed.'
    source = source.replace(old, replacement)
    anchor = '            hose="models/maps/spillway/hose_coil_v2/hose_coil.vmdl"'
    assert source.count(anchor) == 1
    addition = nl.join(['            vent="models/maps/spillway/wall_vent_v2/wall_vent.vmdl"',
        '            root["Children"].append(K.game_object(IDS,"Turbine Wall Vent 1","west/vent1",K.to_world((-1328,220,25)),"0,0,0,1",components=[',
        '                K.component(IDS,"Sandbox.ModelRenderer","west/vent1/renderer",Model=vent,RenderType="On",Tint="1,1,1,1")]))',''])
    source = source.replace(anchor, addition + anchor)
    ast.parse(source)
    stage = WORK / 'install-stage'
    stage.mkdir(exist_ok=True)
    (stage / 'spillway_west.obj').write_bytes('\n'.join(keep).encode('utf-8'))
    (stage / 'spillway.scene').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    (stage / 'spillway_map.py').write_bytes(source.encode('utf-8'))
    files = [mesh, scene, generator]
    hulls = list((ROOT / 'Assets/models/maps/spillway').glob('spillway_west_hulls_*.obj'))
    assert hulls
    manifest = dict(RemovedFaces=len(removed), ObjectGuid=new['__guid'], Expected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        Hulls={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in hulls})
    (WORK / 'install-plan.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))
elif MODE == 'apply':
    plan = json.loads((WORK / 'install-plan.json').read_text())
    with Editor() as editor:
        for name in ('spillway_west.obj','spillway.scene','spillway_map.py'):
            shutil.copy2(WORK / 'install-stage' / name, editor.exchange / name)
        code = '''const string relative = "scenes/maps/spillway/spillway.scene";
var project = Sandbox.Project.Current.GetRootPath();
if (Game.IsPlaying && Game.ActiveScene?.Source?.ResourcePath == relative) throw new InvalidOperationException("Spillway is playing.");
if (Editor.SceneEditorSession.All.Any(s => s.Scene.Source?.ResourcePath == relative)) throw new InvalidOperationException("Spillway is now open; inspect it before installing.");
var asset = Editor.AssetSystem.FindByPath(relative) ?? throw new InvalidOperationException("Missing Spillway scene asset.");
var plan = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(project,"output/asset-improvement-20261030/spillway-vent/install-plan.json")));
string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach (var group in new[] { "Expected", "Hulls" })
    foreach (var entry in plan[group].AsObject())
        if (Hash(System.IO.Path.Combine(project,entry.Key)) != entry.Value.GetValue<string>()) throw new InvalidOperationException("Changed after staging: " + entry.Key);
var model = Model.Load("models/maps/spillway/wall_vent_v2/wall_vent.vmdl");
if (model is null || model.IsError) throw new InvalidOperationException("The approved vent model is invalid.");
var retired = System.IO.Path.Combine(project,"output/asset-improvement-20261030/spillway-vent/retired");
System.IO.Directory.CreateDirectory(retired);
foreach (var entry in plan["Expected"].AsObject())
{
    var path = System.IO.Path.Combine(project,entry.Key);
    var backup = System.IO.Path.Combine(retired,System.IO.Path.GetFileName(path));
    if (System.IO.File.Exists(backup)) throw new InvalidOperationException("Backup exists; inspect installation instead of retrying.");
}
foreach (var entry in plan["Expected"].AsObject())
{
    var path = System.IO.Path.Combine(project,entry.Key);
    System.IO.File.Copy(path,System.IO.Path.Combine(retired,System.IO.Path.GetFileName(path)),false);
}
// Work on the unopened SceneFile through the editor's resource API. The user's active document is untouched.
var resource = asset.LoadResource<SceneFile>();
resource.LoadFromJson(System.IO.File.ReadAllText(System.IO.Path.Combine(exchangeDirectory,"spillway.scene")));
if (!asset.SaveToDisk(resource)) throw new InvalidOperationException("Editor could not save Spillway.");
foreach (var pair in new[] { ("spillway_west.obj","Assets/models/maps/spillway/spillway_west.obj"), ("spillway_map.py","Tools/spillway_map.py") })
{
    var destination = System.IO.Path.Combine(project,pair.Item2);
    var incoming = destination + ".vent-incoming";
    System.IO.File.Copy(System.IO.Path.Combine(exchangeDirectory,pair.Item1),incoming,false);
    System.IO.File.Move(incoming,destination,true);
}
foreach (var entry in plan["Hulls"].AsObject())
    if (Hash(System.IO.Path.Combine(project,entry.Key)) != entry.Value.GetValue<string>()) throw new InvalidOperationException("A west hull changed during installation.");
return new { Installed = "Turbine Wall Vent 1", Position = "220,1328,25", ColliderAdded = false, RemovedFaces = 386, Saved = relative,
    Active = Editor.SceneEditorSession.Active?.Scene.Name, Game.IsPlaying, HullsUnchanged = true };'''
        result = editor.script(code,'install-wall-vent.cs')
        (WORK / 'native-installation.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2),flush=True)
        print(json.dumps(editor.call('asset_compile',dict(path='models/maps/spillway/spillway_west.vmdl'))),flush=True)
elif MODE == 'validate':
    plan = json.loads((WORK / 'install-plan.json').read_text())
    before = json.loads((WORK / 'retired/spillway.scene').read_text())
    after = json.loads((ROOT / 'Assets/scenes/maps/spillway/spillway.scene').read_text())
    root = next(g for g in after['GameObjects'] if g.get('Name') == 'Spillway')
    placed = [g for g in root['Children'] if g.get('__guid') == plan['ObjectGuid']]
    assert len(placed) == 1
    vent = placed[0]
    assert vent['Position'] == '220,1328,25'
    assert [c['__type'] for c in vent['Components']] == ['Sandbox.ModelRenderer']
    root['Children'].remove(vent)
    assert before == after, 'Saved scene has changes beyond the approved vent.'
    assert hashlib.sha256((ROOT / 'Assets/models/maps/spillway/spillway_west.obj').read_bytes()).hexdigest() == hashlib.sha256((WORK / 'install-stage/spillway_west.obj').read_bytes()).hexdigest()
    for path, expected in plan['Hulls'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'West collision hull changed: ' + path
    ast.parse((ROOT / 'Tools/spillway_map.py').read_text())
    print('Static checks passed: only the approved vent object and 386 face cuts; west hulls unchanged.',flush=True)
    template = (ROOT / 'Sources/Spillway/cargo-props-v2/candidates.cs.txt').read_text()
    shots = ', '.join([
        '("standing",new Vector3(300,1170,70),new Vector3(220,1320,70),60f)',
        '("low",new Vector3(285,1218,42),new Vector3(220,1315,67),58f)',
        '("far",new Vector3(370,930,72),new Vector3(220,1320,72),50f)'])
    code = template.replace('%OUT%','output/asset-improvement-20261030/spillway-vent/installed').replace('%SHOTS%',shots)
    # Stream the approved unit's atlas at full resolution while the rest of the map stays at 1024.
    anchor = '    var shots = new (string name, Vector3 eye, Vector3 target, float fov)[]'
    precheck = '''    var vents = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath == "models/maps/spillway/wall_vent_v2/wall_vent.vmdl").ToArray();
    var hoses = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath == "models/maps/spillway/hose_coil_v2/hose_coil.vmdl").ToArray();
    if (vents.Length != 1 || vents[0].Model.IsError || vents[0].GameObject.Components.Get<ModelCollider>() is not null)
        throw new InvalidOperationException("Expected one valid visual-only wall vent.");
    if (hoses.Length != 1 || hoses[0].Model.IsError || hoses[0].GameObject.Components.Get<ModelCollider>() is not null)
        throw new InvalidOperationException("Expected the retained visual-only yard hose.");
    var sharp = vents[0].Model.Materials.SelectMany(m => textureNames.Select(m.GetTexture).Append(m.FirstTexture)).Where(t => t is not null).Distinct().ToArray();
    foreach (var texture in sharp) texture.MarkUsed(2048);
    var rays = new System.Collections.Generic.List<object>();
    using (scene.Push())
    {
        foreach (var ray in new[] {
            ("vent front",new Vector3(220,1200,70),new Vector3(220,1350,70),1,1310f),
            ("vent top",new Vector3(220,1320,200),new Vector3(220,1320,0),2,118f),
            ("in front of old box",new Vector3(220,1305,200),new Vector3(220,1305,-10),2,0f),
            ("unchanged second vent top",new Vector3(1150,1320,200),new Vector3(1150,1320,0),2,118f),
            ("retained hose floor",new Vector3(-1080,-90,50),new Vector3(-1080,-90,-10),2,0f) })
        {
            var hit = scene.Trace.Ray(ray.Item2,ray.Item3).Run();
            var actual = ray.Item4 == 1 ? hit.EndPosition.y : hit.EndPosition.z;
            if (!hit.Hit || Math.Abs(actual-ray.Item5) > .1f) throw new InvalidOperationException("Unexpected collision: " + ray.Item1 + " at " + hit.EndPosition);
            rays.Add(new { Name=ray.Item1, At=hit.EndPosition, Object=hit.GameObject?.Name, Surface=hit.Surface?.ResourceName });
        }
    }
'''
    assert code.count(anchor) == 1
    code = code.replace(anchor, precheck + anchor)
    old_return = 'return new { Written = shots.Length, Renderers = scene.GetAllComponents<ModelRenderer>().Count() };'
    code = code.replace(old_return, 'return new { Vents=vents.Length, Hoses=hoses.Length, AddedColliders=0, Rays=rays, Written=shots.Length, Errors=scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is null || r.Model.IsError).Select(r => r.GameObject.Name).ToArray() };')
    with Editor() as editor:
        result = editor.script(code,'validate-installed-vent.cs')
        print(json.dumps(result,indent=2),flush=True)
        (WORK / 'installed/native-validation.json').write_text(json.dumps(dict(StaticSceneOnlyAddedVent=True,RemovedFaces=386,WestHullsUnchanged=True,Native=result),indent=2))
elif MODE == 'archive':
    assert (WORK / 'installed/native-validation.json').exists(), 'Validate before archiving comparison assets.'
    with Editor() as editor:
        result = editor.script('''var project = Sandbox.Project.Current.GetRootPath();
var source = System.IO.Path.Combine(project,"Assets/models/compare_old/spillway_vent_v2");
var destination = System.IO.Path.Combine(project,"output/asset-improvement-20261030/spillway-vent/retired/comparison_sources");
System.IO.Directory.CreateDirectory(destination);
var files = new System.Collections.Generic.List<string>();
foreach (var stem in new[] { "old_vent", "west_rest" })
    foreach (var suffix in new[] { ".obj", ".obj.meta", ".mtl", ".vmdl", ".vmdl.meta", ".vmdl_c" })
    {
        var name = stem + suffix;
        var path = System.IO.Path.Combine(source,name);
        if (!System.IO.File.Exists(path)) continue;
        System.IO.File.Copy(path,System.IO.Path.Combine(destination,name),false);
        System.IO.File.Delete(path);
        files.Add(name);
    }
return new { Archived=files, SharedHiddenMaterialKept=true };''','archive-vent-review.cs')
        print(json.dumps(result,indent=2))
        (WORK / 'archive-receipt.json').write_text(json.dumps(result,indent=2))
