var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"paving-relief-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected asset changed: "+item.Key);
foreach(var item in manifest["changes"].AsObject())
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 if(System.IO.File.Exists(live))throw new Exception("Candidate already exists; audit before retrying: "+item.Key);
 var source=System.IO.Path.Combine(folder,"paving-relief-stage",item.Key);
 if(Hash(source)!=item.Value["after"].GetValue<string>())throw new Exception("Stage changed: "+item.Key);
}
foreach(var item in manifest["changes"].AsObject().OrderBy(x=>x.Key.EndsWith(".meta")?0:1))
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(live));
 System.IO.File.Copy(System.IO.Path.Combine(folder,"paving-relief-stage",item.Key),live);
 if(!live.EndsWith(".meta"))Editor.AssetSystem.RegisterFile(live);
}
var shaderResult=await Editor.EditorUtility.CompileShader("shaders/hc1_lowtide_paving_relief.shader",new Sandbox.Engine.Shaders.ShaderCompileOptions(),cancellationToken);
if(!shaderResult.Success)throw new Exception("Paving relief shader failed: "+System.Text.Json.JsonSerializer.Serialize(shaderResult));
var compiled=Editor.AssetSystem.FindByPath("materials/lowtide/paving_relief/lt_setts_relief.vmat").Compile(true);
if(!compiled)throw new Exception("Paving candidate material failed to compile");
await Task.Yield();
var material=Material.Load("materials/lowtide/paving_relief/lt_setts_relief.vmat");
var textures=new[]{"g_tColor","g_tNormal","g_tRma","g_tHeight"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray();
if(material.IsError || textures.Any(x=>x.width!=2048||x.height!=2048))throw new Exception("Invalid paving candidate texture binding");
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected asset changed during import: "+item.Key);
var result=new{shader=shaderResult.Success,compiled,material.IsError,textures,
 depth=material.GetVector4("g_flReliefDepth"),scale=material.GetVector4("g_vPavingScale"),region=material.GetVector4("g_vPavingRegion"),
 status="Imported unused candidate; original paving material and model bindings retained",Game.IsPlaying,
 scene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath,dirty=Editor.SceneEditorSession.Active?.HasUnsavedChanges};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"paving-relief-native-compile.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return result;
