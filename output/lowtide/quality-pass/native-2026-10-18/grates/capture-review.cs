var session = Editor.SceneEditorSession.Active;
if (Game.IsPlaying || session?.Scene?.IsEditor != true || session.Scene.Source?.ResourcePath != "scenes/maps/lowtide/lowtide.scene" || Editor.SceneViewWidget.Current?.Session != session) throw new Exception("Expected Lowtide edit viewport");
var folder = System.IO.Path.Combine(Project.Current.GetRootPath(), "output/lowtide/quality-pass/native-2026-10-18/grates/review");
System.IO.Directory.CreateDirectory(folder);
var requests = new[] {
    new { Name="east-large-oblique", Position="-1515,-1140,35", Angles="47.55,-141.34,0" },
    new { Name="east-large-player-height", Position="-1500,-1130,64", Angles="52.0,-143.13,0" },
    new { Name="east-small-oblique", Position="205,-1010,35", Angles="47.55,-141.34,0" },
    new { Name="west-large-oblique", Position="-1515,1140,35", Angles="47.55,141.34,0" }
};
var viewport = Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var originalPosition = viewport.State.CameraPosition;
var originalRotation = viewport.State.CameraRotation;
var results = new System.Collections.Generic.List<object>();
try
{
    foreach (var request in requests)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (Game.IsPlaying || Editor.SceneEditorSession.Active != session || Editor.SceneViewWidget.Current?.Session != session) throw new Exception("Viewport state changed");
        Editor.Mcp.SceneTools.SetEditorCamera(request.Position, request.Angles);
        await Task.Delay(350, cancellationToken);
        if (Game.IsPlaying || Editor.SceneEditorSession.Active != session || Editor.SceneViewWidget.Current?.Session != session) throw new Exception("Viewport state changed");
        Editor.Mcp.SceneTools.SetEditorCamera(request.Position, request.Angles);
        using var bitmap = (Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1600,1000);
        var path = System.IO.Path.Combine(folder, request.Name + ".png");
        System.IO.File.WriteAllBytes(path, bitmap.ToPng());
        results.Add(new { path, camera=Editor.Mcp.SceneTools.GetEditorCamera() });
    }
}
finally
{
    if (!Game.IsPlaying && Editor.SceneEditorSession.Active == session && Editor.SceneViewWidget.Current?.Session == session)
    {
        var angles = originalRotation.Angles();
        Editor.Mcp.SceneTools.SetEditorCamera(
            FormattableString.Invariant($"{originalPosition.x:R},{originalPosition.y:R},{originalPosition.z:R}"),
            FormattableString.Invariant($"{angles.pitch:R},{angles.yaw:R},{angles.roll:R}"));
    }
}
var record = new { results, scene=session.Scene.Source.ResourcePath, session.HasUnsavedChanges, originalPosition, originalRotation, restored=Editor.Mcp.SceneTools.GetEditorCamera() };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"capture.json"), System.Text.Json.JsonSerializer.Serialize(record,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return record;
