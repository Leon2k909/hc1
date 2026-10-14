var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying||session.HasUnsavedChanges||session.Scene.Source.ResourcePath!="scenes/maps/lowtide/lowtide.scene")throw new Exception("Expected clean Lowtide edit scene");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"roof-relief-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach(var pair in manifest["changes"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value["after"].GetValue<string>())throw new Exception("Source changed; refuse rollback: "+pair.Key);
foreach(var pair in manifest["baselineBefore"].AsObject())
    if(Hash(System.IO.Path.Combine(folder,"roof-relief-before",pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Baseline changed: "+pair.Key);
foreach(var ext in new[]{"mtl","obj","vmdl"})
{
    var name="lowtide_finish."+ext;
    var source=System.IO.Path.Combine(folder,"roof-relief-before",name);
    var temp=System.IO.Path.Combine(folder,name+".restore");
    System.IO.File.Copy(source,temp,true);
    System.IO.File.Replace(temp,System.IO.Path.Combine(root,"Assets/models/maps/lowtide",name),null);
}
var compiled=Editor.AssetSystem.FindByPath("models/maps/lowtide/lowtide_finish.vmdl").Compile(true);
if(!compiled)throw new Exception("Restored model failed compilation");
var report=new {compiled,status="rejected geometric slate courses: ground-level aliasing",session.HasUnsavedChanges,Game.IsPlaying};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"roof-relief-rejected.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;
