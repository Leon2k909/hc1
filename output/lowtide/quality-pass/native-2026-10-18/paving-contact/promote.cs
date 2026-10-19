var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/paving-contact");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
var acceptance=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"review/acceptance.json")));
if(!acceptance["accepted"].GetValue<bool>())throw new Exception("Not visually accepted");
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var pair in acceptance["images"].AsObject())
    if(Hash(System.IO.Path.Combine(folder,"review",pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Review changed");
foreach(var pair in data["sources"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Source changed: "+pair.Key);
foreach(var pair in data["staged_files"].AsObject())
{
    if(Hash(System.IO.Path.Combine(folder,"stage",pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Stage changed");
    if(pair.Key!="materials/lowtide/lt_setts.vmat"&&Hash(System.IO.Path.Combine(root,"Assets",pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Imported dependency changed");
}
var material=System.IO.Path.Combine(root,"Assets/materials/lowtide/lt_setts.vmat");
var oldHash=Hash(material);
var backup=System.IO.Path.Combine(folder,"production-before/lt_setts.vmat");
System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
if(System.IO.File.Exists(backup))throw new Exception("Promotion already attempted; inspect current state");
System.IO.File.Copy(material,backup);
var scene=Editor.SceneEditorSession.Active;var playing=Game.IsPlaying;
System.IO.File.WriteAllBytes(material+".native-stage",System.IO.File.ReadAllBytes(System.IO.Path.Combine(folder,"stage/materials/lowtide/lt_setts.vmat")));
System.IO.File.Move(material+".native-stage",material,true);
var report=new{Before=oldHash,After=Hash(material),ScenePreserved=Editor.SceneEditorSession.Active==scene,PlayStatePreserved=Game.IsPlaying==playing,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-import.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
