var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var stage = System.IO.Path.Combine(folder, "piles-stage");
var before = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "piles-before/manifest.json"))).AsObject();
foreach (var pair in before.Where(p => p.Key.StartsWith("Assets/")))
{
    var path = System.IO.Path.Combine(project, pair.Key);
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
    if (hash != pair.Value.GetValue<string>()) throw new Exception($"Changed since pile staging: {pair.Key}");
}
var stagedAssets = System.IO.Path.Combine(stage, "Assets");
var files = System.IO.Directory.GetFiles(stagedAssets, "*", System.IO.SearchOption.AllDirectories);
foreach (var source in files)
{
    var relative = System.IO.Path.GetRelativePath(stagedAssets, source);
    var destination = System.IO.Path.Combine(project, "Assets", relative);
    if (System.IO.File.Exists(destination) && !System.IO.File.ReadAllBytes(destination).SequenceEqual(System.IO.File.ReadAllBytes(source)))
        throw new Exception($"New pile resource already exists with different content: {relative}");
}
foreach (var source in files)
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative = System.IO.Path.GetRelativePath(stagedAssets, source);
    var destination = System.IO.Path.Combine(project, "Assets", relative);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    System.IO.File.Copy(source, destination, true);
    if (!source.EndsWith(".meta")) Editor.AssetSystem.RegisterFile(destination);
}
var shader = await Editor.EditorUtility.CompileShader("shaders/hc1_lowtide_pile.shader", new Sandbox.Engine.Shaders.ShaderCompileOptions(), cancellationToken);
if (!shader.Success) throw new Exception("Pile shader compile failed");
var results = new System.Collections.Generic.List<object>();
foreach (var name in new[] { "lt_pile_timber", "lt_pile_end", "lt_pile_iron" })
{
    cancellationToken.ThrowIfCancellationRequested();
    var path = $"materials/lowtide/piles/{name}.vmat";
    var success = Editor.AssetSystem.FindByPath(path).Compile(false);
    results.Add(new { path, success });
    if (!success) throw new Exception($"Pile material compile failed: {name}");
    await Task.Yield();
}
foreach (var ext in new[] { ".obj", ".mtl", ".vmdl" })
{
    var destination = System.IO.Path.Combine(project, "Assets/models/maps/lowtide/lowtide_fleet" + ext);
    System.IO.File.Copy(System.IO.Path.Combine(stage, "lowtide_fleet" + ext), destination + ".writing", true);
    System.IO.File.Move(destination + ".writing", destination, true);
}
var modelSuccess = Editor.AssetSystem.FindByPath("models/maps/lowtide/lowtide_fleet.vmdl").Compile(false);
results.Add(new { path = "models/maps/lowtide/lowtide_fleet.vmdl", success = modelSuccess });
if (!modelSuccess) throw new Exception("Fleet model compile failed");
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "pile-compile-results.json"), System.Text.Json.JsonSerializer.Serialize(results));
return results;
