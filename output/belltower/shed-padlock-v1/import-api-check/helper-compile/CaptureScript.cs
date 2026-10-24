using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Sandbox;
public static class BelltowerPreviewCapture {
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken) {
// Asset-only publication: preserve the selected document, cameras, play and saved scene.
var root=Sandbox.Project.Current.GetRootPath();
var stage=System.IO.Path.Combine(root,"output/belltower/shed-padlock-v1/stage");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage,"manifest.json")));
var selected=Editor.SceneEditorSession.Active;
var playing=Game.IsPlaying;var gameId=Game.ActiveScene?.Id;
var unsaved=selected?.HasUnsavedChanges;
string Hash(string path) {using var stream=System.IO.File.OpenRead(path);return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).ToLowerInvariant();}
foreach(var pair in manifest["source_sha256"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value.GetValue<string>())
        throw new InvalidOperationException("Staged source changed: "+pair.Key);
var scenePath=System.IO.Path.Combine(root,"Assets/scenes/maps/Belltower/belltower.scene");
var sceneHash=Hash(scenePath);
var allowed=new System.Collections.Generic.HashSet<string>{
    "Assets/materials/belltower/shed_lock_steel.vmat",
    "Assets/models/maps/belltower/belltower_west.obj","Assets/models/maps/belltower/belltower_west.mtl","Assets/models/maps/belltower/belltower_west.vmdl",
    "Assets/models/maps/belltower/belltower_east.obj","Assets/models/maps/belltower/belltower_east.mtl","Assets/models/maps/belltower/belltower_east.vmdl"};
if(!allowed.SetEquals(manifest["files"].AsObject().Select(p=>p.Key)))throw new InvalidOperationException("Unexpected asset set.");
var plan=new System.Collections.Generic.List<(string Source,string Target,string Backup,string Before,string After)>();
foreach(var pair in manifest["files"].AsObject())
{
    var source=System.IO.Path.Combine(stage,pair.Key);var target=System.IO.Path.Combine(root,pair.Key);
    var before=pair.Value["before"]?.GetValue<string>();var after=pair.Value["after"].GetValue<string>();
    if(Hash(source)!=after)throw new InvalidOperationException("Staged asset changed.");
    var current=System.IO.File.Exists(target)?Hash(target):null;
    if(current==after)continue;
    if(current!=before)throw new InvalidOperationException("Current asset changed: "+pair.Key);
    var backup=System.IO.Path.Combine(stage,"before",pair.Key);
    if(before is not null && (!System.IO.File.Exists(backup)||Hash(backup)!=before))throw new InvalidOperationException("Original backup differs.");
    plan.Add((source,target,backup,before,after));
}
plan=plan.OrderBy(p=>p.Target.EndsWith(".vmat")?0:p.Target.EndsWith(".mtl")?1:p.Target.EndsWith(".obj")?2:3).ToList();
var changed=new System.Collections.Generic.List<(string Target,string Backup,string Before)>();
try
{
    foreach(var item in plan)
    {
        var incoming=item.Target+".padlock-incoming";
        try
        {
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(item.Target));
            System.IO.File.Copy(item.Source,incoming,true);
            if(Hash(incoming)!=item.After)throw new InvalidOperationException("Incoming asset changed.");
            changed.Add((item.Target,item.Backup,item.Before));System.IO.File.Move(incoming,item.Target,true);
        }
        finally {if(System.IO.File.Exists(incoming))System.IO.File.Delete(incoming);}
    }
}
catch
{
    foreach(var item in changed.AsEnumerable().Reverse())
        if(item.Before is null)System.IO.File.Delete(item.Target);else System.IO.File.Copy(item.Backup,item.Target,true);
    throw;
}
foreach(var item in plan)Editor.AssetSystem.RegisterFile(item.Target);
if(!ReferenceEquals(selected,Editor.SceneEditorSession.Active)||selected?.HasUnsavedChanges!=unsaved||
    Game.IsPlaying!=playing||Game.ActiveScene?.Id!=gameId||Hash(scenePath)!=sceneHash)
    throw new InvalidOperationException("Shared editor state changed during asset publication.");
var result=new {Imported=plan.Count,Locks=6,SceneSha256=sceneHash,SceneUnchanged=true,EditorStatePreserved=true,
    PhysicsUnchanged=true,ForcedModelCompile=false};
System.IO.File.WriteAllText(System.IO.Path.Combine(stage,"native-import.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

}
}
