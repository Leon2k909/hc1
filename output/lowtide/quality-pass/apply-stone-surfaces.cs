var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var stage = System.IO.Path.Combine(folder, "stone-surfaces-stage/Assets");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "stone-surfaces-before/manifest.json")));
foreach (var pair in manifest["sources"].AsObject().Where(p => p.Key.StartsWith("Assets/")))
{
    var bytes = System.IO.File.ReadAllBytes(System.IO.Path.Combine(project, pair.Key));
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();
    if (hash != pair.Value.GetValue<string>()) throw new Exception($"Stone source changed since staging: {pair.Key}");
}
var files = System.IO.Directory.GetFiles(stage, "*", System.IO.SearchOption.AllDirectories);
foreach (var source in files)
{
    var relative = System.IO.Path.GetRelativePath(stage, source);
    var destination = System.IO.Path.Combine(project, "Assets", relative);
    if (relative.EndsWith(".png") && System.IO.File.Exists(destination) && !System.IO.File.ReadAllBytes(destination).SequenceEqual(System.IO.File.ReadAllBytes(source)))
        throw new Exception($"Stone texture already exists with different content: {relative}");
}
// Register texture inputs before compiling their consumers.
foreach (var source in files.OrderBy(p => p.EndsWith(".meta") ? 0 : p.EndsWith(".png") ? 1 : 2))
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative = System.IO.Path.GetRelativePath(stage, source);
    var destination = System.IO.Path.Combine(project, "Assets", relative);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    System.IO.File.Copy(source, destination + ".writing", true);
    System.IO.File.Move(destination + ".writing", destination, true);
    if (!source.EndsWith(".meta")) Editor.AssetSystem.RegisterFile(destination);
}
var shader = await Editor.EditorUtility.CompileShader("shaders/hc1_lowtide_stone.shader", new Sandbox.Engine.Shaders.ShaderCompileOptions(), cancellationToken);
var result = new System.Collections.Generic.List<object>();
result.Add(new { path = "shaders/hc1_lowtide_stone.shader", success = shader.Success, skipped = shader.Skipped });
if (!shader.Success)
{
    System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "stone-surface-compile-results.json"), System.Text.Json.JsonSerializer.Serialize(result));
    throw new Exception("Stone surface shader compile failed; inspect console diagnostics");
}
foreach (var name in new[] { "lt_tidal_granite", "lt_tidal_brick" })
{
    var relative = $"materials/lowtide/marine/{name}.vmat";
    var success = Editor.AssetSystem.FindByPath(relative).Compile(false);
    result.Add(new { path = relative, success });
    if (!success) throw new Exception($"Stone surface material compile failed: {name}");
    await Task.Yield();
}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "stone-surface-compile-results.json"), System.Text.Json.JsonSerializer.Serialize(result));
return result;
