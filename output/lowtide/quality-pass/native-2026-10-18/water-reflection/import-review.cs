var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/water-reflection");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var pair in data["sources"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Source changed: "+pair.Key);
foreach(var pair in data["files"].AsObject())
{
    if(System.IO.File.Exists(System.IO.Path.Combine(root,pair.Key)))throw new Exception("Target exists: "+pair.Key);
    if(Hash(System.IO.Path.Combine(folder,"stage",pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Stage changed");
}
var scene=Editor.SceneEditorSession.Active;var playing=Game.IsPlaying;
foreach(var pair in data["files"].AsObject())
{
    var path=System.IO.Path.Combine(root,pair.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
    System.IO.File.WriteAllBytes(path+".native-stage",System.IO.File.ReadAllBytes(System.IO.Path.Combine(folder,"stage",pair.Key)));
    System.IO.File.Move(path+".native-stage",path);
}
var report=new{Imported=data["files"].AsObject().Select(p=>p.Key).ToArray(),ScenePreserved=Editor.SceneEditorSession.Active==scene,PlayStatePreserved=Game.IsPlaying==playing,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"review-import.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
