var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/foliage");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"production-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
var changed=new System.Collections.Generic.List<string>();
foreach(var item in manifest["changes"].AsObject())
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 var staged=System.IO.Path.Combine(folder,"production-stage",item.Key);
 if(Hash(staged)!=item.Value["after"].GetValue<string>())throw new Exception("Staged resource changed: "+item.Key);
 var actual=Hash(live);
 if(actual!=item.Value["before"].GetValue<string>()&&actual!=item.Value["after"].GetValue<string>())throw new Exception("Live resource changed: "+item.Key);
 if(actual!=item.Value["after"].GetValue<string>())changed.Add(item.Key);
}
if(changed.Any(p=>p!="materials/lowtide/foliage-v2/lt_oak_branch_v2.vmat"))throw new Exception("Only the accepted tint may change in this import");
foreach(var relative in changed)
 System.IO.File.WriteAllBytes(System.IO.Path.Combine(root,"Assets",relative),System.IO.File.ReadAllBytes(System.IO.Path.Combine(folder,"production-stage",relative)));
var materialPath=manifest["material"].GetValue<string>();
bool compiled=Editor.AssetSystem.FindByPath(materialPath).Compile(true);
var material=Material.Load(materialPath);
var report=new{changed,compiled,material.IsError,material.ShaderName,tint=material.GetVector4("g_flTintColor"),Game.IsPlaying,
 scene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath,status="Accepted material persisted; scene assignment still separate"};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-material-apply.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
if(!compiled||material.IsError)throw new Exception("Material compile failed; inspect the report before retrying");
return report;
