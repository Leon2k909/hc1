if(Game.IsPlaying)throw new Exception("Preserve the running game");
var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/container-surface");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"production-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected source changed: "+item.Key);
foreach(var item in manifest["changes"].AsObject())
{
 var current=Hash(System.IO.Path.Combine(root,"Assets",item.Key));
 if(current!=item.Value["before"].GetValue<string>()&&current!=item.Value["after"].GetValue<string>())throw new Exception("Unexpected material edit: "+item.Key);
 if(Hash(System.IO.Path.Combine(folder,"production-stage",item.Key))!=item.Value["after"].GetValue<string>())throw new Exception("Stage changed: "+item.Key);
}
var results=new System.Collections.Generic.Dictionary<string,bool>();
void Save()=>System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-compile.json"),System.Text.Json.JsonSerializer.Serialize(new{results,Game.IsPlaying,scene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath},new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
foreach(var item in manifest["changes"].AsObject())
{
 cancellationToken.ThrowIfCancellationRequested();
 if(Game.IsPlaying)throw new Exception("Play started; inspect saved report before continuing");
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 if(Hash(live)!=item.Value["after"].GetValue<string>())
 {
  var temporary=live+".writing";
  System.IO.File.Copy(System.IO.Path.Combine(folder,"production-stage",item.Key),temporary,true);
  System.IO.File.Move(temporary,live,true);
 }
 Editor.AssetSystem.RegisterFile(live);
 results[item.Key]=Editor.AssetSystem.FindByPath(item.Key).Compile(true);
 Save();
 if(!results[item.Key])throw new Exception("Material compile failed: "+item.Key);
}
return new{results,status="Six reviewed container materials installed; final loaded-binding and viewport verification pending"};
