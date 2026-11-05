"""Install the approved unit using native scene tools and a guarded editor-side OBJ edit."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3]
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
OUT=ROOT/'output/riverside/roof-ac-v1';plan=json.loads((OUT/'install-plan.json').read_text())
with Editor() as e:
    status=e.call('editor_status')
    assert status['ActiveScenePath'].lower()=='scenes/maps/riverside/riverside.scene' and not status['IsPlaying']
    state=e.script('''var scene=Editor.SceneEditorSession.Active.Scene;
return scene.GetAllObjects(false).Where(g=>g.Name=="Office Rooftop AC"||g.Name=="Roof Air Conditioners").Select(g=>new{g.Id,g.Name,Components=g.Components.GetAll().Count()}).ToArray();''','check-ac-install.cs')
    if state:
        assert '--resume-empty' in sys.argv and len(state)==2 and all(s['Components']==0 for s in state),'Inspect an existing installation before retrying.'
    else:
        assert not status['SceneHasUnsavedChanges']
        e.call('create_game_object',dict(name='Roof Air Conditioners'))
    group=e.script('return Editor.SceneEditorSession.Active.Scene.GetAllObjects(false).Single(g=>g.Name=="Roof Air Conditioners").Id.ToString();','ac-group.cs')
    if not state:e.call('create_game_object',dict(name='Office Rooftop AC',parent=group,position=','.join(map(str,plan['position']))))
    item=e.script('return Editor.SceneEditorSession.Active.Scene.GetAllObjects(false).Single(g=>g.Name=="Office Rooftop AC").Id.ToString();','ac-object.cs')
    e.call('set_game_object',dict(id=item,parent=group,position=','.join(map(str,plan['position']))))
    component=e.call('add_component',dict(id=item,type='ModelRenderer',properties=dict(Model=plan['model'],Tint='1,1,1,1',RenderType='On')))
    (OUT/'native-object.json').write_text(json.dumps(dict(group=group,item=item,component=component),indent=2))
    e.call('save_scene')
    result=e.script(r'''var project=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(project,"output/riverside/roof-ac-v1");
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"install-plan.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
var relative=plan["source"].GetValue<string>();
if(relative.Contains("..")||!relative.StartsWith("Assets/models/"))throw new Exception("Unexpected target");
var target=System.IO.Path.Combine(project,relative);var staged=System.IO.Path.Combine(project,plan["staged"].GetValue<string>());
if(Hash(target)!=plan["source_before"].GetValue<string>()||Hash(staged)!=plan["source_after"].GetValue<string>())throw new Exception("Source changed before AC cut");
System.IO.File.WriteAllBytes(target,System.IO.File.ReadAllBytes(staged));Editor.AssetSystem.RegisterFile(target);
return new {RemovedOldTriangles=24,Source=relative,MatchesStaged=Hash(target)==plan["source_after"].GetValue<string>()};''','cut-old-office-ac.cs')
    assert result['MatchesStaged']
    compiled=e.call('asset_compile',dict(path='models/maps/riverside/riverside_pad.vmdl',full=True))
    assert compiled['Success']
    receipt=dict(scene_object=item,mesh=result,compile=compiled)
    (OUT/'native-install.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
