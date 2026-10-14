// Native visual hot-reload preserves the current match. Collision definitions
// must still match at publication time, as well as in the offline validation.
var beforeScene = Game.ActiveScene?.Id;
var beforePlaying = Game.IsPlaying;
var root = Sandbox.Project.Current.GetRootPath();
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/model-import.json")));
if (manifest["invalid_spots"].GetValue<int>() != 0 || manifest["unreachable_spots"].GetValue<int>() != 0)
    throw new InvalidOperationException("Gameplay validation did not pass.");
var imported = new System.Collections.Generic.List<string>();
foreach(var file in manifest["files"].AsArray())
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative = file["path"].GetValue<string>();
    if (!relative.StartsWith("models/maps/belltower/belltower_",StringComparison.Ordinal) || relative.Contains(".."))
        throw new InvalidOperationException("Unexpected model path.");
    var destination = System.IO.Path.Combine(root,"Assets",relative);
    var backup = System.IO.Path.Combine(root,"output/belltower/quality/before/assets",relative);
    if (System.IO.File.Exists(destination) && !System.IO.File.Exists(backup)) {
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
        System.IO.File.Copy(destination,backup);
    }
    var source = System.IO.Path.GetFullPath(System.IO.Path.Combine(root,file["source"].GetValue<string>()));
    if (!source.StartsWith(System.IO.Path.Combine(root,"output","belltower","quality","models"),StringComparison.OrdinalIgnoreCase))
        throw new InvalidOperationException("Unexpected staging source.");
    if(relative.Contains("_hulls_",StringComparison.Ordinal)) throw new InvalidOperationException("Visual import cannot replace collision hulls.");
    if(relative.EndsWith(".vmdl",StringComparison.Ordinal))
    {
        string Physics(string path) => System.IO.File.ReadAllText(path).Split("_class = \"PhysicsShapeList\"")[1].Split("\n\t\t]\n")[0];
        if(Physics(source)!=Physics(destination)) throw new InvalidOperationException("Collision changed since staging: "+relative);
    }
    using(var sourceStream = System.IO.File.OpenRead(source))
    using(var targetStream = System.IO.File.OpenRead(destination))
        if (System.Security.Cryptography.SHA256.HashData(sourceStream).SequenceEqual(System.Security.Cryptography.SHA256.HashData(targetStream))) continue;
    // ResourceCompiler may still have the old source memory-mapped. Publish a
    // complete new file atomically rather than overwriting that mapped file.
    var incoming = destination + ".belltower-import";
    System.IO.File.Copy(source,incoming,true);
    System.IO.File.Move(incoming,destination,true);
    imported.Add(relative);
}
foreach(var relative in imported.Where(x => x.EndsWith(".vmdl")))
    Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(root,"Assets",relative));
return new { Imported = imported, Models = manifest["models"]?.ToJsonString(), GameplaySpots = manifest["spots"]?.GetValue<int>(),
    MatchPreserved = beforeScene == Game.ActiveScene?.Id && beforePlaying == Game.IsPlaying };
