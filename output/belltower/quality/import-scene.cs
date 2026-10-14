const string relative = "scenes/maps/belltower/belltower.scene";
if (Editor.SceneEditorSession.All.Any(s=>s.Scene.IsEditor && s.Scene.Source?.ResourcePath?.Equals(relative,StringComparison.OrdinalIgnoreCase)==true))
    throw new InvalidOperationException("Belltower is open; use the scene tools so unsaved work is preserved.");
// A running Game scene is an instance, not an editor document. Save its source
// for the next load; never deserialize the full source into the running match.
var beforeScene = Game.ActiveScene?.Id;
var beforePlaying = Game.IsPlaying;
var root = Sandbox.Project.Current.GetRootPath();
var current = System.IO.Path.Combine(root,"Assets",relative);
var staged = System.IO.Path.Combine(root,"output/belltower/quality/scene-import.json");
var expected = System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/scene-import-source.sha256")).Trim();
using(var stream = System.IO.File.OpenRead(current))
    if (!Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).Equals(expected,StringComparison.OrdinalIgnoreCase))
        throw new InvalidOperationException("Scene changed after staging; inspect it and restage before applying.");
var asset = Editor.AssetSystem.FindByPath(relative) ?? throw new InvalidOperationException("Belltower asset is missing.");
var original = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(current));
var incoming = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(staged));
var visual = new System.Collections.Generic.HashSet<string>{"Sun","Sky","Fog","Look","Reflections","Indirect Light","Landscape trees"};
System.Text.Json.Nodes.JsonArray Gameplay(System.Text.Json.Nodes.JsonNode node) => new(node["GameObjects"].AsArray()
    .Where(x=>!visual.Contains(x["Name"]?.GetValue<string>() ?? "")).Select(x=>x.DeepClone()).ToArray());
if(!System.Text.Json.Nodes.JsonNode.DeepEquals(Gameplay(original),Gameplay(incoming))
    || !System.Text.Json.Nodes.JsonNode.DeepEquals(original["SceneProperties"],incoming["SceneProperties"]))
    throw new InvalidOperationException("A visual scene update must preserve gameplay roots and scene properties.");
var resource = asset.LoadResource<SceneFile>();
resource.LoadFromJson(System.IO.File.ReadAllText(staged));
if (!asset.SaveToDisk(resource)) throw new InvalidOperationException("The editor could not save Belltower.");
return new { Saved = relative, Game.IsPlaying, CurrentScene = Game.ActiveScene?.Name,
    MatchPreserved = beforeScene==Game.ActiveScene?.Id && beforePlaying==Game.IsPlaying };
