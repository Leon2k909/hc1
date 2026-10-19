var root = System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if (!string.Equals(root.TrimEnd('\\'), @"C:\sbox-projects\hc1\forked-shooter-main", StringComparison.OrdinalIgnoreCase)) throw new Exception("Wrong project");
var folder = System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/grates");
var m = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p) => System.IO.File.Exists(p) ? Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant() : null;
foreach (var item in m["staged_files"].AsObject())
{
    var path = System.IO.Path.Combine(root,item.Key);
    if (Hash(path) != m["live_before"][item.Key]?.GetValue<string>()) throw new Exception("Live file changed: "+item.Key);
    if (Hash(System.IO.Path.Combine(folder,"stage",item.Key)) != item.Value.GetValue<string>()) throw new Exception("Stage changed: "+item.Key);
}
// Built-in asset_write cannot import models/textures. Import their checked
// sources in the editor and let its asset system register and compile them.
foreach (var item in m["staged_files"].AsObject().OrderBy(p => p.Key.EndsWith(".meta") ? 0 : p.Key.EndsWith(".vmdl") ? 3 : p.Key.EndsWith(".obj") ? 2 : 1))
{
    cancellationToken.ThrowIfCancellationRequested();
    var target = System.IO.Path.Combine(root,item.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
    System.IO.File.Copy(System.IO.Path.Combine(folder,"stage",item.Key),target+".native-stage",true);
    System.IO.File.Move(target+".native-stage",target,true);
    if (item.Key.EndsWith(".png") || item.Key.EndsWith(".vmat") || item.Key.EndsWith(".vmdl")) Editor.AssetSystem.RegisterFile(target);
    if (Hash(target)!=item.Value.GetValue<string>()) throw new Exception("Import failed: "+item.Key);
}
var result = new { Imported = m["staged_files"].AsObject().Count, root, SceneUnchanged = true, Game.IsPlaying, TimeUtc = DateTime.UtcNow };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-import.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;
