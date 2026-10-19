if(Game.IsPlaying)throw new Exception("Stop play before changing model bindings");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2");
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"promotion-plan.json")));
var initial=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in plan["protected"].AsObject())if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected source changed: "+item.Key);
foreach(var item in plan["paintDependencies"].AsObject())if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Paint source changed: "+item.Key);
foreach(var item in plan["resources"].AsObject())
{
    if(Hash(System.IO.Path.Combine(folder,"selected",item.Key))!=item.Value.GetValue<string>())throw new Exception("Selected asset changed");
    if(Hash(System.IO.Path.Combine(root,"Assets",item.Key))!=initial["assets"][item.Key].GetValue<string>())throw new Exception("Imported asset changed");
}
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
foreach(var r in session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_west.vmdl"))
for(int i=0;i<r.Materials.Count;i++)if(r.Materials.GetOverride(i)!=null)throw new Exception("Unexpected architecture material override");
var changed=new System.Collections.Generic.List<string>{"materials/lowtide/structure/lt_cast_iron_v2.vmat"};
foreach(var model in plan["models"].AsArray())
{
    var path=model["path"].GetValue<string>();
    if(Hash(System.IO.Path.Combine(folder,"selected",path))!=model["after"].GetValue<string>())throw new Exception("Selected model changed");
    changed.Add(path);
}
foreach(var path in changed)
{
    cancellationToken.ThrowIfCancellationRequested();
    var backup=System.IO.Path.Combine(folder,"before",path);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    System.IO.File.Copy(System.IO.Path.Combine(root,"Assets",path),backup,false);
    System.IO.File.Copy(System.IO.Path.Combine(folder,"selected",path),System.IO.Path.Combine(root,"Assets",path),true);
}
var report=new{Changed=changed.Select(path=>new{Path=path,Sha256=Hash(System.IO.Path.Combine(root,"Assets",path))}).ToArray(),TimeUtc=DateTime.UtcNow,Game.IsPlaying,session.HasUnsavedChanges};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"promotion.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
