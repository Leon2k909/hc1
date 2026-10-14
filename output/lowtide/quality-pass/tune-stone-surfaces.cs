var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "stone-surface-tune-input.json"))).AsObject();
foreach (var pair in manifest)
{
    var file = System.IO.Path.Combine(project, "Assets", pair.Key);
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(file))).ToLowerInvariant();
    if (hash != pair.Value.GetValue<string>()) throw new Exception($"Material changed before stone tuning: {pair.Key}");
}
var results = new System.Collections.Generic.List<object>();
foreach (var pair in manifest)
{
    var source = System.IO.Path.Combine(folder, "stone-surfaces-stage/Assets", pair.Key);
    var destination = System.IO.Path.Combine(project, "Assets", pair.Key);
    System.IO.File.Copy(source, destination, true);
    var success = Editor.AssetSystem.FindByPath(pair.Key).Compile(false);
    results.Add(new { path = pair.Key, success });
    if (!success) throw new Exception("Stone tuning material compile failed");
}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "stone-surface-final-compile.json"), System.Text.Json.JsonSerializer.Serialize(results));
return results;
