var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in data["protected"].AsObject())if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected input changed: "+item.Key);
foreach(var item in data["assets"].AsObject())
{
    var target=System.IO.Path.Combine(root,"Assets",item.Key);
    if(System.IO.File.Exists(target))throw new Exception("Destination exists: "+item.Key);
    if(Hash(System.IO.Path.Combine(folder,"stage",item.Key))!=item.Value.GetValue<string>())throw new Exception("Stage hash mismatch");
}
foreach(var item in data["assets"].AsObject())
{
    cancellationToken.ThrowIfCancellationRequested();
    var target=System.IO.Path.Combine(root,"Assets",item.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
    System.IO.File.Copy(System.IO.Path.Combine(folder,"stage",item.Key),target,false);
}
var shader=await Editor.EditorUtility.CompileShader("shaders/hc1_lowtide_structure_v2.shader",new Sandbox.Engine.Shaders.ShaderCompileOptions(),cancellationToken);
var registered=data["assets"].AsObject().Where(x=>x.Key.EndsWith(".vmat")).Select(x=>new {Path=x.Key,Registered=Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(root,"Assets",x.Key))!=null}).ToArray();
var report=new {Imported=data["assets"].AsObject().Count,ShaderSuccess=shader.Success,registered,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"import.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
