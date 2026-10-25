using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Sandbox;
public static class BelltowerPreviewCapture {
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken) {
// Publish the reviewed gate-only surgery. No scene edits, play changes or forced
// town-model compilation: the existing asset watcher handles the changed meshes.
var root = Sandbox.Project.Current.GetRootPath();
var stage = System.IO.Path.Combine(root, "output/belltower/gate-v1/stage");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage,"manifest.json")));
var session = Editor.SceneEditorSession.Active;
if (Game.IsPlaying || session is null || session.HasUnsavedChanges
    || !session.Scene.Source.ResourcePath.Equals("scenes/maps/belltower/belltower.scene",StringComparison.OrdinalIgnoreCase))
    throw new InvalidOperationException("Requires the active, stopped, saved Belltower document.");
string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
var scenePath = System.IO.Path.Combine(root,"Assets/scenes/maps/Belltower/belltower.scene");
var sceneHash = Hash(scenePath);
foreach (var pair in manifest["sources"].AsObject())
    if (Hash(System.IO.Path.Combine(root,pair.Key)) != pair.Value.GetValue<string>())
        throw new InvalidOperationException("Staged generator changed: "+pair.Key);
var allowed = new System.Collections.Generic.HashSet<string> {
    "Assets/materials/belltower/gate/forged_iron.vmat",
    "Assets/models/maps/belltower/belltower_west.obj", "Assets/models/maps/belltower/belltower_west.mtl", "Assets/models/maps/belltower/belltower_west.vmdl",
    "Assets/models/maps/belltower/belltower_east.obj", "Assets/models/maps/belltower/belltower_east.mtl", "Assets/models/maps/belltower/belltower_east.vmdl"
};
if (!allowed.SetEquals(manifest["files"].AsObject().Select(p=>p.Key))) throw new InvalidOperationException("Unexpected import set.");
var plan = new System.Collections.Generic.List<(string Source,string Target,string Backup,string Before,string After)>();
foreach (var pair in manifest["files"].AsObject())
{
    var source = System.IO.Path.Combine(stage,pair.Key);
    var target = System.IO.Path.Combine(root,pair.Key);
    var before = pair.Value["before"]?.GetValue<string>();
    var after = pair.Value["after"].GetValue<string>();
    if (Hash(source)!=after) throw new InvalidOperationException("Staged bytes changed: "+pair.Key);
    var current = System.IO.File.Exists(target) ? Hash(target) : null;
    if (current==after) continue;
    if (current!=before) throw new InvalidOperationException("Installed bytes changed: "+pair.Key);
    var backup = System.IO.Path.Combine(stage,"before",pair.Key);
    if (before is not null)
    {
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
        if (!System.IO.File.Exists(backup)) System.IO.File.Copy(target,backup);
        if (Hash(backup)!=before) throw new InvalidOperationException("Backup differs: "+pair.Key);
    }
    plan.Add((source,target,backup,before,after));
}
// Material first, mesh data before model definitions. The model definitions are
// touched last, allowing the watcher to see each complete dependency set.
plan=plan.OrderBy(p=>p.Target.EndsWith(".vmat")?0:p.Target.EndsWith(".mtl")?1:p.Target.EndsWith(".obj")?2:3).ToList();
var changed = new System.Collections.Generic.List<(string Target,string Backup,string Before)>();
try
{
    foreach (var item in plan)
    {
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(item.Target));
        var incoming=item.Target+".gate-incoming";
        System.IO.File.Copy(item.Source,incoming,true);
        try
        {
            if (Hash(incoming)!=item.After) throw new InvalidOperationException("Incoming copy differs.");
            changed.Add((item.Target,item.Backup,item.Before));
            System.IO.File.Move(incoming,item.Target,true);
        }
        finally { if (System.IO.File.Exists(incoming)) System.IO.File.Delete(incoming); }
    }
}
catch
{
    foreach (var item in changed.AsEnumerable().Reverse())
        if (item.Before is null) System.IO.File.Delete(item.Target);
        else System.IO.File.Copy(item.Backup,item.Target,true);
    throw;
}
foreach (var item in plan) Editor.AssetSystem.RegisterFile(item.Target);
if (session.HasUnsavedChanges || Hash(scenePath)!=sceneHash || !ReferenceEquals(session,Editor.SceneEditorSession.Active) || Game.IsPlaying)
    throw new InvalidOperationException("Editor or scene state changed during publication.");
var result = new {Imported=plan.Count, Files=plan.Select(p=>p.Target), SceneSha256=sceneHash,
    SceneUnchanged=true, PhysicsUnchanged=manifest["physics_unchanged"].GetValue<bool>(),
    TrianglesAddedPerGate=manifest["triangles_added_per_half"].GetValue<int>(), ForcedModelCompile=false};
System.IO.File.WriteAllText(System.IO.Path.Combine(stage,"native-import.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

}
}
