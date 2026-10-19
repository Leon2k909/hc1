var root = System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if (!string.Equals(root.TrimEnd('\\'), @"C:\sbox-projects\hc1\forked-shooter-main", StringComparison.OrdinalIgnoreCase)) throw new Exception("Wrong project");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/construction-recomposed/native-review");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"import-manifest.json")));
string Hash(string p) => System.IO.File.Exists(p) ? Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant() : null;
foreach (var item in manifest["production_before"].AsObject())
    if (Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>()) throw new Exception("Production source changed: "+item.Key);
foreach (var item in manifest["files"].AsObject())
{
    if (System.IO.File.Exists(System.IO.Path.Combine(root,item.Key))) throw new Exception("Review destination already exists: "+item.Key);
    if (Hash(System.IO.Path.Combine(folder,"stage",item.Key))!=item.Value.GetValue<string>()) throw new Exception("Review stage changed: "+item.Key);
}
var imported=new System.Collections.Generic.List<string>();
foreach (var item in manifest["files"].AsObject().OrderBy(p=>p.Key.EndsWith(".vmdl")?3:p.Key.EndsWith(".vmat")?2:p.Key.EndsWith(".shader")?1:0))
{
    cancellationToken.ThrowIfCancellationRequested();
    var target=System.IO.Path.Combine(root,item.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
    System.IO.File.Copy(System.IO.Path.Combine(folder,"stage",item.Key),target,false);
    if (item.Key.EndsWith(".vmdl")||item.Key.EndsWith(".vmat")||item.Key.EndsWith(".shader")) Editor.AssetSystem.RegisterFile(target);
    imported.Add(item.Key);
}
var result=new{Imported=imported,ProductionUnchanged=true,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-import.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;
