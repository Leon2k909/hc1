var session = Editor.SceneEditorSession.Active;
var view = Editor.SceneViewWidget.Current;
var viewport = view?.LastSelectedViewportWidget;
var includes = FileSystem.Mounted.FindFile("shaders", "*.hlsl", true)
    .Where(p => p.Contains("env", StringComparison.OrdinalIgnoreCase)
             || p.Contains("ambient", StringComparison.OrdinalIgnoreCase)
             || p.Contains("depth", StringComparison.OrdinalIgnoreCase)).ToArray();
return new {
    Scene = session?.Scene.Source?.ResourcePath,
    Dirty = session?.HasUnsavedChanges,
    ViewScene = view?.Session?.Scene.Source?.ResourcePath,
    CameraPosition = viewport?.State.CameraPosition.ToString(),
    CameraRotation = viewport?.State.CameraRotation.Angles().ToString(),
    Cameras = session?.Scene.GetAllComponents<CameraComponent>().Select(c => new {
        c.GameObject.Name, c.Active, c.Orthographic, Position = c.WorldPosition.ToString(),
        Angles = c.WorldRotation.Angles().ToString()
    }).ToArray(),
    Includes = includes,
    exchangeDirectory
};
