"""Native installation of both approved ceiling fixtures; no lighting or physics edits."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/fluorescent-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
plan=json.loads((OUT/'install-plan.json').read_text())
with Editor() as e:
    status=e.call('editor_status')
    assert not status['IsPlaying'],'Preserve active play mode.'
    if status['ActiveScenePath'].lower()!='scenes/maps/riverside/riverside.scene':
        e.call('open_scene',dict(path='scenes/maps/Riverside/riverside.scene'))
    created=e.script(r'''var session=Editor.SceneEditorSession.Active;
if(session.Scene.Source?.ResourcePath?.Equals("scenes/maps/riverside/riverside.scene",StringComparison.OrdinalIgnoreCase)!=true||session.HasUnsavedChanges||Game.IsPlaying)throw new Exception("Riverside must be a clean edited document");
if(session.Scene.GetAllObjects(false).Any(g=>g.Name=="Store Ceiling Lights"))throw new Exception("Installation already started");
var group=Editor.Mcp.SceneTools.CreateGameObject(name:"Store Ceiling Lights");
var items=new System.Collections.Generic.List<string>();
var model="models/props/riverside/fluorescent_v1/fixture.vmdl";
var positions=new[]{"760,-150,145.4","890,-280,145.4"};
for(var i=0;i<positions.Length;i++)
{
    var item=Editor.Mcp.SceneTools.CreateGameObject(name:$"Store Fluorescent {i+1}",parent:group.Id.ToString(),position:positions[i]);
    var props=new System.Text.Json.Nodes.JsonObject { ["Model"]=model,["Tint"]="1,1,1,1",["RenderType"]="On" };
    Editor.Mcp.SceneTools.AddComponent(item.Id.ToString(),"ModelRenderer",props);items.Add(item.Id.ToString());
}
Editor.Mcp.SceneTools.SaveScene();
return new {Group=group.Id,Objects=items};''','create-approved-fluorescents.cs')
    objects=created['Objects']
    (OUT/'native-objects.json').write_text(json.dumps(created,indent=2))
    result=e.script(r'''var project=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(project,"output/riverside/fluorescent-v1");
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"install-plan.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
var relative=plan["source"].GetValue<string>();
if(relative.Contains("..")||!relative.StartsWith("Assets/models/"))throw new Exception("Unexpected target");
var target=System.IO.Path.Combine(project,relative);var staged=System.IO.Path.Combine(project,plan["staged"].GetValue<string>());
if(Hash(target)!=plan["source_before"].GetValue<string>()||Hash(staged)!=plan["source_after"].GetValue<string>())throw new Exception("Source changed before fixture cut");
System.IO.File.WriteAllBytes(target,System.IO.File.ReadAllBytes(staged));Editor.AssetSystem.RegisterFile(target);
return new{RemovedOldTriangles=28,Source=relative,MatchesStaged=Hash(target)==plan["source_after"].GetValue<string>()};''','cut-old-fluorescents.cs')
    assert result['MatchesStaged']
    compiled=e.call('asset_compile',dict(path='models/maps/riverside/riverside_store.vmdl',full=True));assert compiled['Success']
    report=dict(objects=objects,mesh=result,compile=compiled)
    current=e.call('editor_status')
    if status['ActiveScenePath'].lower()!='scenes/maps/riverside/riverside.scene' and current['ActiveScenePath'].lower()=='scenes/maps/riverside/riverside.scene' and not current['SceneHasUnsavedChanges']:
        e.call('switch_scene',dict(scene=status['ActiveScenePath']))
    report['editor_before']=status
    report['editor_after']=e.call('editor_status')
    (OUT/'native-install.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
