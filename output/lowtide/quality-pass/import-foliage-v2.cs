var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/foliage");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"v2-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach(var item in manifest["changes"].AsObject())
{
 if(!item.Key.StartsWith("materials/lowtide/foliage-v2/")&&!item.Key.StartsWith("shaders/hc1_lowtide_foliage_v2"))throw new Exception("Unexpected candidate path");
 if(System.IO.File.Exists(System.IO.Path.Combine(root,"Assets",item.Key)))throw new Exception("Candidate already exists; inspect before retrying: "+item.Key);
 if(Hash(System.IO.Path.Combine(folder,"v2-stage",item.Key))!=item.Value.GetValue<string>())throw new Exception("Candidate stage changed");
}
foreach(var item in manifest["changes"].AsObject().OrderBy(x=>x.Key.EndsWith(".meta")?0:1))
{
 var target=System.IO.Path.Combine(root,"Assets",item.Key);
 System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
 System.IO.File.Copy(System.IO.Path.Combine(folder,"v2-stage",item.Key),target);
 if(!target.EndsWith(".meta")&&!target.EndsWith(".hlsl"))Editor.AssetSystem.RegisterFile(target);
}
var results=new System.Collections.Generic.Dictionary<string,bool>();
void Save()=>System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"v2-compile.json"),System.Text.Json.JsonSerializer.Serialize(new{results,Game.IsPlaying,scene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath},new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
Save();
var shader=await Editor.EditorUtility.CompileShader("shaders/hc1_lowtide_foliage_v2.shader",new Sandbox.Engine.Shaders.ShaderCompileOptions(),cancellationToken);
results["shader"]=shader.Success;
Save();
if(!shader.Success)throw new Exception(System.Text.Json.JsonSerializer.Serialize(shader));
var material="materials/lowtide/foliage-v2/lt_oak_branch_v2.vmat";
results[material]=Editor.AssetSystem.FindByPath(material).Compile(true);
Save();
return new{results,status="Unused private foliage candidate imported; game, scene and cloud tree resources unchanged"};
