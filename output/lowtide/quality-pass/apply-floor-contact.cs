var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var stage = System.IO.Path.Combine(folder, "floor-contact-stage/Assets");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "floor-contact-before/manifest.json")));
foreach (var pair in manifest["sources"].AsObject().Where(p => p.Key.StartsWith("Assets/")))
{
    var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(System.IO.Path.Combine(project, pair.Key)))).ToLowerInvariant();
    if (hash != pair.Value.GetValue<string>()) throw new Exception($"Source changed since staging: {pair.Key}");
}
foreach (var source in System.IO.Directory.GetFiles(stage, "*", System.IO.SearchOption.AllDirectories).OrderBy(p => p.EndsWith(".meta") ? 0 : p.EndsWith(".png") ? 1 : 2))
{
    var relative = System.IO.Path.GetRelativePath(stage, source);
    var destination = System.IO.Path.Combine(project, "Assets", relative);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    System.IO.File.Copy(source, destination, true);
    if (!source.EndsWith(".meta")) Editor.AssetSystem.RegisterFile(destination);
}
var result = await Editor.EditorUtility.CompileShader("shaders/hc1_lowtide_concrete.shader", new Sandbox.Engine.Shaders.ShaderCompileOptions(), cancellationToken);
if (!result.Success) return new { shader = false };
var material = Editor.AssetSystem.FindByPath("materials/lowtide/interior/lt_concrete.vmat").Compile(false);
return new { shader = result.Success, material };
