var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var stage = System.IO.Path.Combine(folder, "window-stage");
var backup = System.IO.Path.Combine(folder, "window-before");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage, "manifest.json")));
var assets = new System.Collections.Generic.List<(string Name, Editor.Asset Asset, string Obj)>();
foreach (var name in new[] { "lowtide_east", "lowtide_west", "lowtide_backdrop" })
{
    var asset = Editor.AssetSystem.FindByPath($"models/maps/lowtide/{name}.vmdl");
    if (asset == null) throw new Exception($"Missing architecture {name}");
    var obj = System.IO.Path.ChangeExtension(asset.AbsolutePath, ".obj");
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(obj))).ToLowerInvariant();
    if (hash != manifest[name]["sha256"].GetValue<string>()) throw new Exception($"{name} changed since staging; regenerate the scoped UV patch");
    assets.Add((name, asset, obj));
}
System.IO.Directory.CreateDirectory(backup);
var results = new System.Collections.Generic.List<object>();
foreach (var item in assets)
{
    cancellationToken.ThrowIfCancellationRequested();
    var source = System.IO.File.ReadAllText(item.Asset.AbsolutePath);
    const string original = "materials/railhead/rw_window_dark.vmat";
    const string replacement = "materials/lowtide/windows/lt_window_interior.vmat";
    if (!source.Contains(original)) throw new Exception($"Unexpected window material on {item.Name}");
    foreach (var path in new[] { item.Asset.AbsolutePath, item.Obj })
    {
        var saved = System.IO.Path.Combine(backup, System.IO.Path.GetFileName(path));
        if (!System.IO.File.Exists(saved)) System.IO.File.Copy(path, saved);
    }
    var stagedObj = System.IO.Path.Combine(stage, item.Name + ".obj");
    System.IO.File.Copy(stagedObj, item.Obj + ".writing", true);
    System.IO.File.Move(item.Obj + ".writing", item.Obj, true);
    System.IO.File.WriteAllText(item.Asset.AbsolutePath + ".writing", source.Replace(original, replacement));
    System.IO.File.Move(item.Asset.AbsolutePath + ".writing", item.Asset.AbsolutePath, true);
    results.Add(new { name=item.Name, success=item.Asset.Compile(false) });
    await Task.Yield();
}
return results;
