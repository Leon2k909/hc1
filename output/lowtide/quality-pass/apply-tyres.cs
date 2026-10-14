var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var stage = System.IO.Path.Combine(folder, "tyres-stage");
var before = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "tyres-before/manifest.json"))).AsObject();
foreach (var pair in before.Where(p => p.Key.StartsWith("Assets/")))
{
    var bytes = System.IO.File.ReadAllBytes(System.IO.Path.Combine(project, pair.Key));
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();
    if (hash != pair.Value.GetValue<string>()) throw new Exception($"Changed since tyre staging: {pair.Key}");
}
var relative = "materials/lowtide/tyres/lt_discarded_tyre.vmat";
var destination = System.IO.Path.Combine(project, "Assets", relative);
var source = System.IO.Path.Combine(stage, "Assets", relative);
foreach (var suffix in new[] { "", ".meta" })
{
    if (System.IO.File.Exists(destination + suffix) && !System.IO.File.ReadAllBytes(destination + suffix).SequenceEqual(System.IO.File.ReadAllBytes(source + suffix)))
        throw new Exception("Tyre resource already exists with different content");
}
System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
System.IO.File.Copy(source + ".meta", destination + ".meta", true);
System.IO.File.Copy(source, destination, true);
Editor.AssetSystem.RegisterFile(destination);
var materialSuccess = Editor.AssetSystem.FindByPath(relative).Compile(false);
if (!materialSuccess) throw new Exception("Discarded tyre material compile failed");
cancellationToken.ThrowIfCancellationRequested();
foreach (var ext in new[] { ".obj", ".mtl", ".vmdl" })
{
    var output = System.IO.Path.Combine(project, "Assets/models/maps/lowtide/lowtide_fleet" + ext);
    System.IO.File.Copy(System.IO.Path.Combine(stage, "lowtide_fleet" + ext), output + ".writing", true);
    System.IO.File.Move(output + ".writing", output, true);
}
var modelSuccess = Editor.AssetSystem.FindByPath("models/maps/lowtide/lowtide_fleet.vmdl").Compile(false);
var result = new { materialSuccess, modelSuccess };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "tyre-compile-results.json"), System.Text.Json.JsonSerializer.Serialize(result));
if (!modelSuccess) throw new Exception("Fleet model compile failed");
return result;
