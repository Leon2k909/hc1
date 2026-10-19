var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/water-reflection");
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"retire-review-plan.json")))["files"].AsObject();
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
var stems=new[]{"Assets/materials/lowtide/water-review/lt_water_filter_review.vmat","Assets/models/maps/lowtide/lowtide_water_filter_review.vmdl"};
var permitted=stems.SelectMany(p=>new[]{p,p+".meta",p+"_c"}).ToArray();
foreach(var entry in plan)
{
    if(!permitted.Contains(entry.Key))throw new Exception("Unexpected cleanup path");
    var path=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,entry.Key));
    if(!path.StartsWith(System.IO.Path.Combine(root,"Assets")+System.IO.Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Outside assets");
    if(Hash(path)!=entry.Value.GetValue<string>())throw new Exception("Temporary file changed");
    if(System.IO.File.Exists(System.IO.Path.Combine(folder,"retired-review",entry.Key)))throw new Exception("Review archive already exists");
}
var scenes=Editor.SceneEditorSession.All.Select(s=>s.Scene).Append(Game.ActiveScene).Where(s=>s!=null).Distinct();
foreach(var scene in scenes)
foreach(var renderer in scene.GetAllComponents<ModelRenderer>())
{
    if(renderer.Model?.ResourcePath=="models/maps/lowtide/lowtide_water_filter_review.vmdl")throw new Exception("Review model is in use");
    if(renderer.Model?.Materials.Any(m=>m.ResourcePath=="materials/lowtide/water-review/lt_water_filter_review.vmat")==true)throw new Exception("Review material is in use");
}
var active=Editor.SceneEditorSession.Active;var playing=Game.IsPlaying;
foreach(var entry in plan)
{
    var path=System.IO.Path.Combine(root,entry.Key);var backup=System.IO.Path.Combine(folder,"retired-review",entry.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    System.IO.File.Copy(path,backup);
    if(Hash(backup)!=entry.Value.GetValue<string>())throw new Exception("Archive mismatch");
}
foreach(var entry in plan)System.IO.File.Delete(System.IO.Path.Combine(root,entry.Key));
var report=new{Archived=plan.Select(p=>p.Key).ToArray(),Removed=plan.All(p=>!System.IO.File.Exists(System.IO.Path.Combine(root,p.Key))),ScenePreserved=Editor.SceneEditorSession.Active==active,PlayStatePreserved=Game.IsPlaying==playing,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"review-retired.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
