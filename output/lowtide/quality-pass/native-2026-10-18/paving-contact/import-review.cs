var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/paving-contact");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var pair in data["sources"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Source changed: "+pair.Key);
var writes=new System.Collections.Generic.Dictionary<string,byte[]>();
foreach(var pair in data["staged_files"].AsObject())
{
    var input=System.IO.Path.Combine(folder,"stage",pair.Key);
    if(Hash(input)!=pair.Value.GetValue<string>())throw new Exception("Stage changed");
    var rel=pair.Key=="materials/lowtide/lt_setts.vmat"?"materials/lowtide/paving-use/lt_setts_review.vmat":pair.Key;
    var path=System.IO.Path.Combine(root,"Assets",rel);
    if(System.IO.File.Exists(path))throw new Exception("Review target already exists: "+rel);
    writes.Add(rel,System.IO.File.ReadAllBytes(input));
}
var scene=Editor.SceneEditorSession.Active;var playing=Game.IsPlaying;
foreach(var pair in writes)
{
    var path=System.IO.Path.Combine(root,"Assets",pair.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
    System.IO.File.WriteAllBytes(path+".native-stage",pair.Value);
    System.IO.File.Move(path+".native-stage",path);
}
var report=new{Imported=writes.Keys.ToArray(),ProductionMaterialUnchanged=Hash(System.IO.Path.Combine(root,"Assets/materials/lowtide/lt_setts.vmat"))==data["sources"]["Assets/materials/lowtide/lt_setts.vmat"].GetValue<string>(),ActiveScenePreserved=Editor.SceneEditorSession.Active==scene,PlayStatePreserved=Game.IsPlaying==playing,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"review-import.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
