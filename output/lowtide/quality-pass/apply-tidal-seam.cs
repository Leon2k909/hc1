var session = Editor.SceneEditorSession.Active;
if ( Game.IsPlaying || session is null || session.HasUnsavedChanges || session.Scene.Source.ResourcePath != "scenes/maps/lowtide/lowtide.scene" )
    throw new Exception("Expected saved Lowtide scene outside play mode");
var root = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"tidal-seam-manifest.json")));
string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
foreach (var pair in manifest["protectedBefore"].AsObject())
{
    cancellationToken.ThrowIfCancellationRequested();
    if (Hash(System.IO.Path.Combine(root,pair.Key)) != pair.Value.GetValue<string>()) throw new Exception("Source changed since staging: "+pair.Key);
}
foreach (var pair in manifest["changes"].AsObject())
{
    var staged = System.IO.Path.Combine(folder,"tidal-seam-stage",System.IO.Path.GetFileName(pair.Key));
    if (Hash(staged) != pair.Value["after"].GetValue<string>()) throw new Exception("Stage hash mismatch: "+pair.Key);
}
foreach (var pair in manifest["changes"].AsObject())
{
    // Replace the directory entry atomically: the asset browser memory-maps
    // source OBJs, so overwriting their existing storage fails on Windows.
    var filename = System.IO.Path.GetFileName(pair.Key);
    var replacement = System.IO.Path.Combine(folder,"tidal-seam-stage",filename+".replace");
    System.IO.File.Copy(System.IO.Path.Combine(folder,"tidal-seam-stage",filename),replacement,true);
    System.IO.File.Replace(replacement,System.IO.Path.Combine(root,pair.Key),null);
}
var results = new System.Collections.Generic.List<object>();
foreach (var name in new[]{"lowtide_east","lowtide_west","lowtide_finish"})
{
    cancellationToken.ThrowIfCancellationRequested();
    var path = "models/maps/lowtide/"+name+".vmdl";
    var asset = Editor.AssetSystem.FindByPath(path) ?? throw new Exception("Missing model asset: "+path);
    var compiled = asset.Compile(true);
    results.Add(new { path, compiled });
    if (!compiled) throw new Exception("Model compile failed: "+path);
    await Task.Yield();
}
var report = new { results, scene = session.Scene.Source.ResourcePath, session.HasUnsavedChanges, Game.IsPlaying };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"tidal-seam-native-compile.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;
