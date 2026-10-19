var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"promotion.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var pair in data["protected"].AsObject())
    if(Hash(System.IO.Path.Combine(root,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Input changed: "+pair.Key);
foreach(var pair in data["resources"].AsObject())
    if(Hash(System.IO.Path.Combine(root,"Assets",pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Resource changed: "+pair.Key);
var models=data["models"].AsObject().ToArray();
foreach(var model in models)
{
    if(Hash(System.IO.Path.Combine(root,"Assets",model.Key))!=model.Value["before"].GetValue<string>())throw new Exception("Model changed: "+model.Key);
    if(Hash(System.IO.Path.Combine(folder,"promotion",model.Key))!=model.Value["after"].GetValue<string>())throw new Exception("Stage changed: "+model.Key);
}
var active=Editor.SceneEditorSession.Active;var playing=Game.IsPlaying;
foreach(var model in models)
{
    var destination=System.IO.Path.Combine(root,"Assets",model.Key);
    var backup=System.IO.Path.Combine(folder,"binding-before",model.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    System.IO.File.Copy(destination,backup,false);
    System.IO.File.WriteAllBytes(destination+".native-stage",System.IO.File.ReadAllBytes(System.IO.Path.Combine(folder,"promotion",model.Key)));
    System.IO.File.Move(destination+".native-stage",destination,true);
}
var report=new{Applied=models.Select(p=>new{Path=p.Key,Hash=Hash(System.IO.Path.Combine(root,"Assets",p.Key))}).ToArray(),Remaps=4,ScenePreserved=Editor.SceneEditorSession.Active==active,PlayStatePreserved=Game.IsPlaying==playing,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"binding-import.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
