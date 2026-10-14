var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var stage = System.IO.Path.Combine(folder, "banks-stage");
var root = System.IO.Path.Combine(project, "Assets/models/maps/lowtide");
var expected = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage, "revision-replaces.json"))).AsObject();
foreach (var pair in expected)
{
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(System.IO.Path.Combine(root, pair.Key)))).ToLowerInvariant();
    if (hash != pair.Value.GetValue<string>()) throw new Exception($"Changed since bank revision staging: {pair.Key}");
}
var results = new System.Collections.Generic.List<object>();
foreach (var name in new[] { "lowtide_marine", "lowtide_finish" })
{
    cancellationToken.ThrowIfCancellationRequested();
    if (System.IO.File.ReadAllText(System.IO.Path.Combine(stage, name + ".vmdl")).Contains("Physics")) throw new Exception("Bank detail must remain visual-only");
    foreach (var ext in new[] { ".obj", ".mtl", ".vmdl" })
    {
        var destination = System.IO.Path.Combine(root, name + ext);
        System.IO.File.Copy(System.IO.Path.Combine(stage, name + ext), destination + ".writing", true);
        System.IO.File.Move(destination + ".writing", destination, true);
    }
    var asset = Editor.AssetSystem.FindByPath($"models/maps/lowtide/{name}.vmdl");
    var success = asset.Compile(false);
    results.Add(new { path = name, success });
    if (!success) throw new Exception($"Visual mesh compile failed: {name}");
    await Task.Yield();
}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "bank-revision-compile-results.json"), System.Text.Json.JsonSerializer.Serialize(results));
return results;
