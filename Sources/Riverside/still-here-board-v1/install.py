"""Install the approved hitch with guarded native scene tools and exact mesh surgery."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/still-here-board-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
with Editor() as e:
    status=e.call('editor_status')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT.resolve()
    if status['IsPlaying']: e.call('play_stop')
    if status['ActiveScenePath'].lower()!='scenes/maps/riverside/riverside.scene':
        e.call('open_scene',dict(path='scenes/maps/Riverside/riverside.scene'))
    try:
        result=e.script(r'''var session=Editor.SceneEditorSession.Active;
if(session.Scene.Source?.ResourcePath?.Equals("scenes/maps/riverside/riverside.scene",StringComparison.OrdinalIgnoreCase)!=true||session.HasUnsavedChanges||Game.IsPlaying)throw new Exception("Riverside must be a clean edited document");
if(session.Scene.GetAllObjects(false).Any(g=>g.Name=="Park Graffiti Boards"))throw new Exception("Installation already started");
var model=Model.Load("models/props/riverside/still_here_board_v1/board.vmdl");
if(model.IsError||!model.MeshInfo.Meshes.Select(m=>m.Triangles).SequenceEqual(new[]{896,752,144}))throw new Exception("Approved hitch mesh differs");
var project=Sandbox.Project.Current.GetRootPath();var folder=System.IO.Path.Combine(project,"output/riverside/still-here-board-v1");
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"install-plan.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
var relative=plan["source"].GetValue<string>();
if(relative.Contains("..")||!relative.StartsWith("Assets/models/maps/riverside/"))throw new Exception("Unexpected mesh target");
var target=System.IO.Path.Combine(project,relative);var staged=System.IO.Path.Combine(project,plan["staged"].GetValue<string>());
if(Hash(target)!=plan["source_before"].GetValue<string>()||Hash(staged)!=plan["source_after"].GetValue<string>())throw new Exception("Source changed before hitch cut");
var group=Editor.Mcp.SceneTools.CreateGameObject(name:"Park Graffiti Boards");
var item=Editor.Mcp.SceneTools.CreateGameObject(name:"STILL HERE Board",parent:group.Id.ToString(),position:"411.535923789485,390.99995599854793,261.25",angles:"0,30.000727780827372,0");
Editor.Mcp.SceneTools.AddComponent(item.Id.ToString(),"ModelRenderer",new System.Text.Json.Nodes.JsonObject{["Model"]=model.ResourcePath,["Tint"]="1,1,1,1",["RenderType"]="On"});
Editor.Mcp.SceneTools.SaveScene();
var checkpoint=new{Group=group.Id,Object=item.Id,SceneSaved=true,Source=relative};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-objects.json"),System.Text.Json.JsonSerializer.Serialize(checkpoint));
System.IO.File.WriteAllBytes(target,System.IO.File.ReadAllBytes(staged));Editor.AssetSystem.RegisterFile(target);
return new{Group=group.Id,Object=item.Id,SceneSaved=true,RemovedOldTriangles=14,MatchesStaged=Hash(target)==plan["source_after"].GetValue<string>()};''','install-approved-tv-hitch.cs')
        (OUT/'native-install.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
    finally:
        current=e.call('editor_status')
        if status['ActiveScenePath'].lower()!='scenes/maps/riverside/riverside.scene' and current['ActiveScenePath'].lower()=='scenes/maps/riverside/riverside.scene' and not current['SceneHasUnsavedChanges'] and not current['IsPlaying']:
            e.call('switch_scene',dict(scene=status['ActiveScenePath']))
            if status['IsPlaying']: e.call('play_start')
    result=e.call('asset_compile',dict(path='models/maps/riverside/riverside_dressing.vmdl'))
    (OUT/'native-install-compile.json').write_text(json.dumps(result,indent=2));assert result['Success'];print(json.dumps(result),flush=True)
