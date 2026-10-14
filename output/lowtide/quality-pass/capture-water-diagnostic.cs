var session = Editor.SceneEditorSession.Active;
if (Game.IsPlaying || session?.Scene.Source?.ResourcePath != "scenes/maps/lowtide/lowtide.scene") throw new Exception("Expected Lowtide edit viewport");
var folder = System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass");
var requests = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"viewport-request.json"))).AsArray();
var viewport = Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var originalPosition = viewport.State.CameraPosition;
var originalRotation = viewport.State.CameraRotation;
var results = new System.Collections.Generic.List<string>();
try
{
    foreach (var request in requests)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var name = request["name"].GetValue<string>();
        if (System.IO.Path.GetFileName(name) != name) throw new Exception("Expected simple capture name");
        Editor.Mcp.SceneTools.SetEditorCamera(request["position"].GetValue<string>(),request["angles"].GetValue<string>());
        await Task.Delay(250,cancellationToken);
        // Navigation inertia can update the native camera while yielding.
        // Reapply immediately before rendering to retain the requested view.
        Editor.Mcp.SceneTools.SetEditorCamera(request["position"].GetValue<string>(),request["angles"].GetValue<string>());
        foreach(var water in session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>())water.PrepareViews();
        using var bitmap = (Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
        var path = System.IO.Path.Combine(folder,name+".png");
        System.IO.File.WriteAllBytes(path,bitmap.ToPng());
        results.Add(path);
    }
}
finally
{
    var angles=originalRotation.Angles();
    Editor.Mcp.SceneTools.SetEditorCamera(
        FormattableString.Invariant($"{originalPosition.x:R},{originalPosition.y:R},{originalPosition.z:R}"),
        FormattableString.Invariant($"{angles.pitch:R},{angles.yaw:R},{angles.roll:R}"));
    foreach(var water in session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>())water.PrepareViews();
}
return new { results, scene=session.Scene.Source.ResourcePath, session.HasUnsavedChanges,
    originalPosition, originalRotation, restored=Editor.Mcp.SceneTools.GetEditorCamera() };
