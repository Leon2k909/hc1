var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
var folder=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/structure-response"));
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in data["protected"].AsObject())if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected input changed: "+item.Key);
var materials=data["assets"].AsObject().Select(x=>x.Key).Where(p=>p.EndsWith(".vmat")).ToArray();
foreach(var session in Editor.SceneEditorSession.All)
foreach(var renderer in session.Scene.GetAllComponents<ModelRenderer>())
{
    if(renderer.Model?.Materials.Any(m=>materials.Contains(m.ResourcePath))==true)throw new Exception("Candidate bound by a model");
    if(materials.Contains(renderer.MaterialOverride?.ResourcePath))throw new Exception("Candidate used by an override");
    for(int i=0;i<renderer.Materials.Count;i++)if(materials.Contains(renderer.Materials.GetOverride(i)?.ResourcePath))throw new Exception("Candidate used by a slot override");
}
var assets=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"Assets"))+System.IO.Path.DirectorySeparatorChar;
foreach(var item in data["assets"].AsObject())
{
    var live=System.IO.Path.GetFullPath(System.IO.Path.Combine(assets,item.Key));
    var copy=System.IO.Path.GetFullPath(System.IO.Path.Combine(folder,"stage",item.Key));
    if(!live.StartsWith(assets,StringComparison.OrdinalIgnoreCase)||!copy.StartsWith(folder+System.IO.Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Unexpected cleanup path");
    if(Hash(live)!=item.Value.GetValue<string>()||Hash(copy)!=item.Value.GetValue<string>())throw new Exception("Candidate source changed; inspect before cleanup");
}
foreach(var item in data["assets"].AsObject())System.IO.File.Delete(System.IO.Path.Combine(assets,item.Key));
var report=new {RetiredSources=data["assets"].AsObject().Count,StagedCopiesPreserved=true,CompiledCachesUntouched=true,AllProductionInputsUnchanged=true,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"retired.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
