var root = Sandbox.Project.Current.GetRootPath();
var stage = System.IO.Path.Combine(root,"output/veridant/breakable-rails-v1/stage");
var assets = System.IO.Path.Combine(root,"Assets");
var plan = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage,"plan.json")));
foreach(var item in plan["imports"].AsArray()) {
    var source=item["source"].GetValue<string>();
    var hash=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(source))).ToLowerInvariant();
    if(hash!=item["sha256"].GetValue<string>()) throw new Exception("Import changed: "+source);
}
// Publish new assets first. Keep the original static panes until every replacement compiles.
var resource="models/maps/veridant/breakable-rails-v1";
foreach(var file in System.IO.Directory.GetFiles(System.IO.Path.Combine(stage,resource))) {
    var destination=System.IO.Path.Combine(assets,resource,System.IO.Path.GetFileName(file));
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    System.IO.File.Copy(file,destination,true);
}
var bad=new System.Collections.Generic.List<string>();
foreach(var node in plan["models"].AsArray()) {
    cancellationToken.ThrowIfCancellationRequested();
    var path=node.GetValue<string>();
    var asset=Editor.AssetSystem.FindByPath(path) ?? Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(assets,path));
    if(asset is null || !await asset.CompileIfNeededAsync()) bad.Add(path);
}
return new {Compiled=plan["models"].AsArray().Count,Problems=bad};
