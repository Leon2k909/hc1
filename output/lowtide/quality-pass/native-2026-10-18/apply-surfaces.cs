var root = System.IO.Path.GetFullPath(Project.Current.GetRootPath());
var expectedRoot = System.IO.Path.GetFullPath(@"C:\sbox-projects\hc1\forked-shooter-main");
if (!string.Equals(root.TrimEnd('\\'), expectedRoot.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
    throw new Exception("Wrong project");
var session = Editor.SceneEditorSession.Active;
if (Game.IsPlaying || session?.Scene?.Source?.ResourcePath != "scenes/maps/lowtide/lowtide.scene")
    throw new Exception("Expected Lowtide edit scene");
var folder = System.IO.Path.Combine(root, "output/lowtide/quality-pass/native-2026-10-18");
var stageRoot = System.IO.Path.Combine(root, "output/lowtide/quality-pass/rebase-2026-10-18");
string Hash(string path) => System.IO.File.Exists(path)
    ? Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant() : null;
var entries = new System.Collections.Generic.List<(string Relative, string Source, string Before, string After)>();
foreach (var name in new[] { "water-filter-gentle", "paving-use" })
{
    var stage = System.IO.Path.Combine(stageRoot, name);
    var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage, "manifest.json")));
    foreach (var pair in manifest["staged_files"].AsObject())
    {
        var relative = name.StartsWith("water") ? pair.Key : "Assets/" + pair.Key;
        var source = System.IO.Path.Combine(stage, "stage", pair.Key);
        var before = manifest["live_before"][pair.Key]?.GetValue<string>();
        var after = pair.Value.GetValue<string>();
        if (Hash(source) != after) throw new Exception("Staged bytes changed: " + relative);
        if (Hash(System.IO.Path.Combine(root, relative)) != before) throw new Exception("Live file changed: " + relative);
        entries.Add((relative, source, before, after));
    }
}
// Back up all overwritten files before making any changes. The source snapshots
// are accepted only after every live before-hash matched above.
foreach (var entry in entries.Where(e => e.Before != null))
{
    var backup = System.IO.Path.Combine(folder, "before", entry.Relative);
    if (System.IO.File.Exists(backup) && Hash(backup) != entry.Before)
        throw new Exception("Different backup already exists: " + entry.Relative);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    if (!System.IO.File.Exists(backup)) System.IO.File.Copy(System.IO.Path.Combine(root, entry.Relative), backup);
}
foreach (var entry in entries.OrderBy(e => e.Relative.StartsWith("Code/") ? 3 : e.Relative.EndsWith(".vmat") ? 2 : e.Relative.EndsWith(".meta") ? 0 : 1))
{
    cancellationToken.ThrowIfCancellationRequested();
    var destination = System.IO.Path.Combine(root, entry.Relative);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    var temporary = destination + ".native-stage";
    System.IO.File.Copy(entry.Source, temporary, true);
    System.IO.File.Move(temporary, destination, true);
    if (entry.Relative.StartsWith("Assets/") && !entry.Relative.EndsWith(".meta"))
        Editor.AssetSystem.RegisterFile(destination);
    if (Hash(destination) != entry.After) throw new Exception("Write verification failed: " + entry.Relative);
}
var result = new { ProjectRoot = root, Written = entries.Select(e => new { e.Relative, e.Before, e.After }).ToArray(),
    SceneChanged = session.HasUnsavedChanges, NativeVisualAcceptance = false, TimeUtc = DateTime.UtcNow };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "installed.json"), System.Text.Json.JsonSerializer.Serialize(result, new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
return result;
