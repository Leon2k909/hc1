var project = Project.Current.GetRootPath();
var beforeFolder = System.IO.Path.Combine(project, "output/lowtide/quality-pass/roof-before");
System.IO.Directory.CreateDirectory(beforeFolder);
const string original = "materials/buildings/slate.vmat";
const string replacement = "materials/lowtide/roofs/lt_slate.vmat";
var material = Editor.AssetSystem.FindByPath(replacement);
if (material == null) throw new Exception("New slate material has not registered");
if (!material.Compile(false)) throw new Exception("Slate material compilation failed");
var report = new System.Collections.Generic.List<object>();
foreach (var name in new[] { "lowtide_east", "lowtide_west" })
{
    cancellationToken.ThrowIfCancellationRequested();
    var asset = Editor.AssetSystem.FindByPath($"models/maps/lowtide/{name}.vmdl");
    if (asset == null) throw new Exception($"Missing model {name}");
    var source = System.IO.File.ReadAllText(asset.AbsolutePath);
    if (!source.Contains(original) && !source.Contains(replacement))
        throw new Exception($"Unexpected slate remap in {name}");
    var backup = System.IO.Path.Combine(beforeFolder, name + ".vmdl");
    if (!System.IO.File.Exists(backup)) System.IO.File.WriteAllText(backup, source);
    var updated = source.Replace(original, replacement);
    if (updated.Replace(replacement, original) != source.Replace(replacement, original))
        throw new Exception("Material-only replacement changed unrelated source");
    if (updated != source) System.IO.File.WriteAllText(asset.AbsolutePath, updated);
    report.Add(new { name, success=asset.Compile(false), material=replacement });
}
return report;
