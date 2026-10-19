var folder = System.IO.Path.Combine(Project.Current.GetRootPath(), "output/lowtide/shore-fix-20261017");
foreach (var file in new[]{"EnvMap", "AmbientLight", "Depth"})
    System.IO.File.WriteAllText(System.IO.Path.Combine(folder, file + ".hlsl"),
        FileSystem.Mounted.ReadAllText("shaders/common/classes/" + file + ".hlsl"));
var scene = Game.ActiveScene;
return new {
    Playing = Game.IsPlaying,
    Sessions = Editor.SceneEditorSession.All.Select(s => new {
        s.Scene.Name, Path = s.Scene.Source?.ResourcePath, s.Scene.IsEditor,
        s.HasUnsavedChanges, Active = s == Editor.SceneEditorSession.Active
    }).ToArray(),
    Water = scene.GetAllComponents<ModelRenderer>().Where(r => r.GameObject.Name == "Water").Select(r => new {
        r.Id, r.GameObject.Name, Model = r.Model?.ResourcePath,
        Position = r.WorldPosition.ToString(), Scale = r.WorldScale.ToString(),
        Materials = Enumerable.Range(0, r.Materials.Count).Select(i => new {
            Original = r.Materials.GetOriginal(i)?.ResourcePath,
            Override = r.Materials.GetOverride(i)?.ResourcePath
        }).ToArray()
    }).ToArray(),
    Probes = scene.GetAllComponents<EnvmapProbe>().Select(p => new {
        p.Id, p.GameObject.Name, Position = p.WorldPosition.ToString(),
        p.Bounds, p.Feathering, p.Projection
    }).ToArray()
};
