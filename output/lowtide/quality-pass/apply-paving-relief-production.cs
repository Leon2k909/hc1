var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var session=Editor.SceneEditorSession.All.FirstOrDefault(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session?.HasUnsavedChanges==true)throw new Exception("Lowtide has unsaved edits");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"paving-relief-production-manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected source changed: "+item.Key);
foreach(var item in manifest["changes"].AsObject())
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 if(Hash(live)!=item.Value["before"].GetValue<string>())throw new Exception("Paving material changed; inspect before retrying");
 var staged=System.IO.Path.Combine(folder,"paving-relief-production",item.Key);
 if(Hash(staged)!=item.Value["after"].GetValue<string>())throw new Exception("Staged material changed");
}
foreach(var item in manifest["changes"].AsObject())
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 var staged=System.IO.Path.Combine(folder,"paving-relief-production",item.Key);
 var temporary=staged+".replace";
 System.IO.File.Copy(staged,temporary,true);
 System.IO.File.Replace(temporary,live,null);
}
var compiled=Editor.AssetSystem.FindByPath("materials/lowtide/lt_setts.vmat").Compile(true);
if(!compiled)throw new Exception("Production paving material failed to compile");
await Task.Yield();
var material=Material.Load("materials/lowtide/lt_setts.vmat");
var textures=new[]{"g_tColor","g_tNormal","g_tRma","g_tHeight"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray();
if(material.IsError||textures.Any(x=>x.width!=2048||x.height!=2048))throw new Exception("Invalid production texture binding");
var slots=session?.Scene.GetAllComponents<ModelRenderer>().SelectMany(renderer=>Enumerable.Range(0,renderer.Materials.Count)
 .Where(i=>renderer.Materials.GetOriginal(i)?.ResourcePath==material.ResourcePath)
 .Select(i=>new{name=renderer.GameObject.Name,index=i,hasOverride=renderer.Materials.GetOverride(i)!=null})).ToArray();
if(slots!=null&&(slots.Length!=3||slots.Any(x=>x.hasOverride)))throw new Exception("Unexpected production paving slots");
var report=new{compiled,material.IsError,textures,slots,depth=material.GetVector4("g_flReliefDepth"),lowtideOpen=session!=null,
 sceneDirty=session?.HasUnsavedChanges,Game.IsPlaying,activeScene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"paving-relief-production-compile.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
