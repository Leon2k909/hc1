var root = System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if (!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main", StringComparison.OrdinalIgnoreCase)) throw new Exception("Wrong checkout");
var folder = System.IO.Path.Combine(root, "output/lowtide/quality-pass/native-2026-10-18/construction-recomposed");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "native-review/import-manifest.json")));
var readback = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "production-readback.json")));
if (!readback["AllMatch"].GetValue<bool>()) throw new Exception("Production comparison missing");
var sceneBefore = Editor.SceneEditorSession.Active;
var playingBefore = Game.IsPlaying;
var renderers = Editor.SceneEditorSession.All.SelectMany(s => s.Scene.GetAllComponents<ModelRenderer>()).ToArray();
if (renderers.Any(r => (r.Model?.ResourcePath ?? "").Contains("/construction_review/") ||
    Enumerable.Range(0, r.Materials.Count).Any(i => (r.Materials.GetOriginal(i)?.ResourcePath ?? "").Contains("/construction_review/"))))
    throw new Exception("A comparison asset remains in an open scene");
string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
var files = new System.Collections.Generic.Dictionary<string,string>();
foreach (var pair in manifest["files"].AsObject().Where(p => p.Key.Contains("/construction_review/")))
{
    var absolute = System.IO.Path.GetFullPath(System.IO.Path.Combine(root, pair.Key));
    var allowed = new[]{"Assets/models/maps/lowtide/construction_review/", "Assets/materials/lowtide/finish/construction_review/"};
    if (!allowed.Any(p => absolute.StartsWith(System.IO.Path.GetFullPath(System.IO.Path.Combine(root,p)), StringComparison.OrdinalIgnoreCase))) throw new Exception("Unexpected path");
    if (Hash(absolute) != pair.Value.GetValue<string>()) throw new Exception("Review source changed: " + pair.Key);
    files.Add(pair.Key, Hash(absolute));
    if (pair.Key.EndsWith(".vmdl") || pair.Key.EndsWith(".vmat"))
        foreach (var suffix in new[]{".meta", "_c"})
            if (System.IO.File.Exists(absolute + suffix)) files.Add(pair.Key + suffix, Hash(absolute + suffix));
}
foreach (var pair in files)
{
    var from = System.IO.Path.Combine(root, pair.Key);
    var backup = System.IO.Path.Combine(folder, "retired-review", pair.Key);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    if (System.IO.File.Exists(backup) && Hash(backup) != pair.Value) throw new Exception("Backup conflict");
    System.IO.File.Copy(from, backup, true);
    if (Hash(backup) != pair.Value) throw new Exception("Backup failed");
}
foreach (var pair in files)
{
    var absolute = System.IO.Path.Combine(root, pair.Key);
    if (Hash(absolute) != pair.Value) throw new Exception("Review changed while archiving");
    System.IO.File.Delete(absolute);
}
var report = new{ArchivedFiles=files,ProductionShaderPreserved=System.IO.File.Exists(System.IO.Path.Combine(root,"Assets/shaders/hc1_lowtide_finish_metal.shader")),ActiveScenePreserved=Editor.SceneEditorSession.Active==sceneBefore,PlayStatePreserved=Game.IsPlaying==playingBefore,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"review-retired.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return new{Archived=files.Count,report.ProductionShaderPreserved,report.ActiveScenePreserved,report.PlayStatePreserved};
