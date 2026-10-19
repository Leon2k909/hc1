var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var pair in data["protected"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Input changed: "+pair.Key);
var resources=data["assets"].AsObject().Where(p=>!p.Key.EndsWith(".vmdl")).OrderBy(p=>p.Key.EndsWith(".meta")?0:p.Key.EndsWith(".hlsl")?1:p.Key.EndsWith(".png")?2:p.Key.EndsWith(".shader")?3:4).ToArray();
foreach(var entry in resources)
{
    if(Hash(System.IO.Path.Combine(folder,"stage",entry.Key))!=entry.Value.GetValue<string>())throw new Exception("Stage changed");
    if(System.IO.File.Exists(System.IO.Path.Combine(root,"Assets",entry.Key)))throw new Exception("Target exists: "+entry.Key);
}
var active=Editor.SceneEditorSession.Active;var playing=Game.IsPlaying;
foreach(var entry in resources)
{
    var destination=System.IO.Path.Combine(root,"Assets",entry.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    System.IO.File.WriteAllBytes(destination+".native-stage",System.IO.File.ReadAllBytes(System.IO.Path.Combine(folder,"stage",entry.Key)));
    System.IO.File.Move(destination+".native-stage",destination);
}
var report=new{Imported=resources.Select(p=>p.Key).ToArray(),ProductionModelBindingsChanged=false,ScenePreserved=Editor.SceneEditorSession.Active==active,PlayStatePreserved=Game.IsPlaying==playing,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"resource-import.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
