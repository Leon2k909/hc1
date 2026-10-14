var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var stage = System.IO.Path.Combine(folder, "banks-stage");
var before = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(
    System.IO.Path.Combine(folder, "banks-before/manifest.json"))).AsObject();
var materials = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage, "materials.json"))).AsObject();
// Verify all replaced asset sources before applying anything. Other chats may
// edit the same project while the staged geometry is being prepared.
foreach (var pair in before.Where(p => p.Key.StartsWith("Assets/") && !p.Key.EndsWith(".shader")))
{
    var path = System.IO.Path.Combine(project, pair.Key);
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
    var relative = pair.Key.Substring("Assets/".Length);
    var alreadyApplied = materials.TryGetPropertyValue(relative, out var material)
        && System.IO.File.ReadAllText(path) == material.GetValue<string>();
    if (hash != pair.Value.GetValue<string>() && !alreadyApplied) throw new Exception($"Changed since bank staging: {pair.Key}");
}
var results = new System.Collections.Generic.List<object>();
foreach (var pair in materials)
{
    cancellationToken.ThrowIfCancellationRequested();
    var path = System.IO.Path.Combine(project, "Assets", pair.Key);
    System.IO.File.WriteAllText(path + ".writing", pair.Value.GetValue<string>());
    System.IO.File.Move(path + ".writing", path, true);
    var asset = Editor.AssetSystem.FindByPath(pair.Key) ?? Editor.AssetSystem.RegisterFile(path);
    if (asset == null) throw new Exception($"Could not register {pair.Key}");
    var success = asset.Compile(false);
    results.Add(new { path = pair.Key, success });
    if (!success) throw new Exception($"Material compile failed: {pair.Key}");
    await Task.Yield();
}
foreach (var name in new[] { "lowtide_marine", "lowtide_finish" })
{
    var asset = Editor.AssetSystem.FindByPath($"models/maps/lowtide/{name}.vmdl");
    if (asset == null) throw new Exception($"Missing visual mesh {name}");
    var text = System.IO.File.ReadAllText(System.IO.Path.Combine(stage, name + ".vmdl"));
    if (text.Contains("Physics")) throw new Exception("Bank detail must remain visual-only");
    foreach (var ext in new[] { ".obj", ".mtl", ".vmdl" })
    {
        var destination = System.IO.Path.ChangeExtension(asset.AbsolutePath, ext);
        System.IO.File.Copy(System.IO.Path.Combine(stage, name + ext), destination + ".writing", true);
        System.IO.File.Move(destination + ".writing", destination, true);
    }
    var success = asset.Compile(false);
    results.Add(new { path = name, success });
    if (!success) throw new Exception($"Visual mesh compile failed: {name}");
    await Task.Yield();
}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "bank-compile-results.json"),
    System.Text.Json.JsonSerializer.Serialize(results));
return results;
