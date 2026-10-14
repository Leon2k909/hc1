var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var materials = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "banks-stage/materials.json"))).AsObject();
var results = new System.Collections.Generic.List<object>();
foreach (var pair in materials.Where(p => p.Key.Contains("/marine/")))
{
    cancellationToken.ThrowIfCancellationRequested();
    System.IO.File.WriteAllText(System.IO.Path.Combine(project, "Assets", pair.Key), pair.Value.GetValue<string>());
    var asset = Editor.AssetSystem.FindByPath(pair.Key);
    var success = asset.Compile(false);
    results.Add(new { path = pair.Key, success });
    if (!success) throw new Exception($"Material compile failed: {pair.Key}");
    await Task.Yield();
}
return results;
