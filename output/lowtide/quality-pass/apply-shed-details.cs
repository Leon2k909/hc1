var session=Editor.SceneEditorSession.Active;
if (Game.IsPlaying || session is null || session.HasUnsavedChanges || session.Scene.Source.ResourcePath!="scenes/maps/lowtide/lowtide.scene") throw new Exception("Expected saved Lowtide edit scene");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"shed-details-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach(var pair in manifest["protectedBefore"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Source changed since staging: "+pair.Key);
foreach(var pair in manifest["changes"].AsObject())
{
    var staged=System.IO.Path.Combine(folder,"shed-details-stage",System.IO.Path.GetFileName(pair.Key));
    if(Hash(staged)!=pair.Value["after"].GetValue<string>())throw new Exception("Invalid stage: "+pair.Key);
}
foreach(var extension in new[]{"mtl","obj","vmdl"})
{
    cancellationToken.ThrowIfCancellationRequested();
    var name="lowtide_finish."+extension;
    var staged=System.IO.Path.Combine(folder,"shed-details-stage",name);
    var replacement=staged+".replace";
    System.IO.File.Copy(staged,replacement,true);
    System.IO.File.Replace(replacement,System.IO.Path.Combine(root,"Assets/models/maps/lowtide",name),null);
}
var asset=Editor.AssetSystem.FindByPath("models/maps/lowtide/lowtide_finish.vmdl");
var compiled=asset.Compile(true);
if(!compiled)throw new Exception("Shed details model failed to compile");
await Task.Yield();
var renderer=session.Scene.GetAllComponents<ModelRenderer>().First(r=>r.GameObject.Name=="Harbour Details");
var report=new {compiled,model=renderer.Model.ResourcePath,renderer.Model.IsError,
    materialErrors=renderer.Model.Materials.Where(m=>m is null || m.IsError).Count(),
    scene=session.Scene.Source.ResourcePath,session.HasUnsavedChanges,Game.IsPlaying};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"shed-details-native-compile.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;
