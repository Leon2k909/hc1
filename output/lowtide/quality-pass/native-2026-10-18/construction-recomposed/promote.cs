var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!string.Equals(root.TrimEnd('\\'),@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/construction-recomposed");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
var canonical=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"canonical-verification.json")));
var review=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"native-review/visual-review.json")));
if(!review["accepted"].GetValue<bool>())throw new Exception("Visual review not accepted");
string Hash(string p)=>System.IO.File.Exists(p)?Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant():null;
foreach(var item in canonical["generator_sources"].AsObject())if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Generator changed after verification: "+item.Key);
foreach(var item in manifest["protected_models"].AsObject())if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Production model changed: "+item.Key);
var changes=new System.Collections.Generic.List<string>();
foreach(var item in manifest["staged_files"].AsObject())
{
    var after=item.Value.GetValue<string>();
    if(Hash(System.IO.Path.Combine(folder,"stage",item.Key))!=after)throw new Exception("Stage changed: "+item.Key);
    var current=Hash(System.IO.Path.Combine(root,item.Key));
    if(current==after)continue;
    if(current!=manifest["live_before"][item.Key]?.GetValue<string>())throw new Exception("Live source changed: "+item.Key);
    changes.Add(item.Key);
}
var scenePath=System.IO.Path.Combine(root,"Assets/scenes/maps/Lowtide/lowtide.scene");
var sceneHash=Hash(scenePath);
var active=Editor.SceneEditorSession.Active;
var wasPlaying=Game.IsPlaying;
foreach(var relative in changes)
{
    cancellationToken.ThrowIfCancellationRequested();
    var path=System.IO.Path.Combine(root,relative);
    var backup=System.IO.Path.Combine(folder,"production-before",relative);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    if(System.IO.File.Exists(backup))throw new Exception("Backup already exists; inspect prior import: "+relative);
    System.IO.File.Copy(path,backup,false);
}
foreach(var relative in changes.OrderBy(p=>p.EndsWith(".obj")?1:0))
{
    cancellationToken.ThrowIfCancellationRequested();
    var path=System.IO.Path.Combine(root,relative);
    // Write fresh timestamps so dependency checking cannot retain an older compiled mesh.
    System.IO.File.WriteAllBytes(path+".native-stage",System.IO.File.ReadAllBytes(System.IO.Path.Combine(folder,"stage",relative)));
    System.IO.File.Move(path+".native-stage",path,true);
    if(relative.EndsWith(".vmat"))Editor.AssetSystem.RegisterFile(path);
    if(Hash(path)!=manifest["staged_files"][relative].GetValue<string>())throw new Exception("Import mismatch: "+relative);
}
if(Hash(scenePath)!=sceneHash)throw new Exception("Saved Lowtide scene changed during import");
var result=new{Imported=changes,SceneHash=sceneHash,ActiveScenePreserved=Editor.SceneEditorSession.Active==active,PlayStatePreserved=Game.IsPlaying==wasPlaying,Scene=active?.Scene?.Source?.ResourcePath,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-import.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return result;
