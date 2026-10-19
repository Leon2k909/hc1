var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
if(Game.IsPlaying)throw new Exception("Apply container geometry while editing");
var session=Editor.SceneEditorSession.All.FirstOrDefault(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session?.HasUnsavedChanges==true)throw new Exception("Lowtide has unsaved edits");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/container-detail");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected source changed: "+item.Key);
foreach(var item in manifest["changes"].AsObject())
{
 if(Hash(System.IO.Path.Combine(root,"Assets",item.Key))!=item.Value["before"].GetValue<string>())throw new Exception("Live model changed; inspect before retrying");
 if(Hash(System.IO.Path.Combine(folder,"stage",item.Key))!=item.Value["after"].GetValue<string>())throw new Exception("Stage changed");
}
foreach(var item in manifest["changes"].AsObject())
{
 var live=System.IO.Path.Combine(root,"Assets",item.Key);
 var staged=System.IO.Path.Combine(folder,"stage",item.Key);
 var temporary=staged+".replace";
 System.IO.File.Copy(staged,temporary,true);
 System.IO.File.Replace(temporary,live,null);
}
var report=new{status="Both scoped OBJ replacements saved; native model compilation and viewport review are next",Game.IsPlaying,sceneDirty=session?.HasUnsavedChanges,changed=manifest["changes"].AsObject().Select(x=>x.Key).ToArray()};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"applied.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
