var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying || session?.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene" || session.HasUnsavedChanges)throw new Exception("Expected saved Lowtide edit viewport");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"roof-response-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected asset changed: "+item.Key);
foreach(var item in manifest["changes"].AsObject())
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 var old=item.Value["before"]?.GetValue<string>();
 if(old==null ? System.IO.File.Exists(live) : !System.IO.File.Exists(live)||Hash(live)!=old)throw new Exception("Preview baseline changed: "+item.Key);
 var source=System.IO.Path.Combine(folder,"roof-response-stage",item.Key);
 if(Hash(source)!=item.Value["after"].GetValue<string>())throw new Exception("Stage changed: "+item.Key);
}
foreach(var item in manifest["changes"].AsObject().OrderBy(x=>x.Key.EndsWith(".meta")?0:1))
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 var source=System.IO.Path.Combine(folder,"roof-response-stage",item.Key);
 System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(live));
 if(System.IO.File.Exists(live))
 {
  var temporary=source+".replace";
  System.IO.File.Copy(source,temporary,true);
  System.IO.File.Replace(temporary,live,null);
 }
 else System.IO.File.Copy(source,live);
 if(!live.EndsWith(".meta"))Editor.AssetSystem.RegisterFile(live);
}
var shaderResult=await Editor.EditorUtility.CompileShader("shaders/hc1_slate.shader",new Sandbox.Engine.Shaders.ShaderCompileOptions(),cancellationToken);
var shader=shaderResult.Success;
if(!shader)throw new Exception("Slate shader failed to compile");
var compiled=Editor.AssetSystem.FindByPath("materials/lowtide/roofs/lt_slate.vmat").Compile(true);
if(!compiled)throw new Exception("Slate material failed to compile");
await Task.Yield();
var material=Material.Load("materials/lowtide/roofs/lt_slate.vmat");
var result=new {shader,compiled,material.IsError,tint=material.GetVector4("g_flTintColor"),scale=material.GetVector4("g_vSlateScale"),textures=new[]{"g_tColor","g_tNormal","g_tRma"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray(),session.HasUnsavedChanges};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"roof-response-native-compile.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return result;
