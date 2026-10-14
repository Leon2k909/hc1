var project = Project.Current.GetRootPath();
var results = new System.Collections.Generic.List<object>();
foreach (var side in new[] { "east", "west" })
{
    var name = $"lowtide_{side}.vmdl";
    var asset = Editor.AssetSystem.FindByPath($"models/maps/lowtide/{name}");
    if (asset == null) throw new Exception($"Missing Lowtide {side} model");
    var source = System.IO.File.ReadAllText(asset.AbsolutePath);
    const string original = "materials/railhead/rw_concrete.vmat";
    const string replacement = "materials/lowtide/interior/lt_concrete.vmat";
    if (!source.Contains(original) && !source.Contains(replacement)) throw new Exception("Unexpected floor source");
    var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass/interior-before");
    System.IO.Directory.CreateDirectory(folder);
    var backup = System.IO.Path.Combine(folder, name);
    if (!System.IO.File.Exists(backup)) System.IO.File.WriteAllText(backup, source);
    var updated = source.Replace(original, replacement);
    if (updated != source) System.IO.File.WriteAllText(asset.AbsolutePath, updated);
    results.Add(new { side, success = asset.Compile(false), material = replacement });
}
return results;
