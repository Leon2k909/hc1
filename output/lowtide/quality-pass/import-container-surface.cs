var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/container-surface");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected source changed: "+item.Key);
foreach(var item in manifest["changes"].AsObject())
{
 if(System.IO.File.Exists(System.IO.Path.Combine(root,"Assets",item.Key)))throw new Exception("Candidate already exists; inspect before retrying");
 if(Hash(System.IO.Path.Combine(folder,"stage",item.Key))!=item.Value["after"].GetValue<string>())throw new Exception("Stage changed");
}
foreach(var item in manifest["changes"].AsObject().OrderBy(x=>x.Key.EndsWith(".meta")?0:1))
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(live));
 System.IO.File.Copy(System.IO.Path.Combine(folder,"stage",item.Key),live);
 if(!live.EndsWith(".meta"))Editor.AssetSystem.RegisterFile(live);
}
var results=new System.Collections.Generic.Dictionary<string,bool>();
void Save()=>System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-compile.json"),System.Text.Json.JsonSerializer.Serialize(new{results,Game.IsPlaying,scene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath},new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
Save();
var shader=await Editor.EditorUtility.CompileShader("shaders/hc1_lowtide_container.shader",new Sandbox.Engine.Shaders.ShaderCompileOptions(),cancellationToken);
results["shader"]=shader.Success;
Save();
if(!shader.Success)throw new Exception(System.Text.Json.JsonSerializer.Serialize(shader));
foreach(var path in manifest["changes"].AsObject().Select(x=>x.Key).Where(x=>x.EndsWith(".vmat")))
{
 cancellationToken.ThrowIfCancellationRequested();
 results[path]=Editor.AssetSystem.FindByPath(path).Compile(true);
 Save();
 if(!results[path])throw new Exception("Material compile failed: "+path);
}
return new{results,status="Unused candidates imported and compiled; production materials unchanged"};
