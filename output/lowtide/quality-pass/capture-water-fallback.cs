var session = Editor.SceneEditorSession.Active;
if (Game.IsPlaying || session?.Scene.Source?.ResourcePath != "scenes/maps/lowtide/lowtide.scene") throw new Exception("Expected Lowtide edit viewport");
var viewport = Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var pos = viewport.State.CameraPosition;
var rot = viewport.State.CameraRotation;
var waters = session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Select(x => (component:x, enabled:x.Enabled)).ToArray();
var path = System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/water-fallback-diagnostic.png");
try
{
    foreach(var item in waters) item.component.Enabled=false;
    Editor.Mcp.SceneTools.SetEditorCamera("-1300,0,125","-2.503,0,0");
    await Task.Delay(250,cancellationToken);
    Editor.Mcp.SceneTools.SetEditorCamera("-1300,0,125","-2.503,0,0");
    using var bitmap = (Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
    System.IO.File.WriteAllBytes(path,bitmap.ToPng());
}
finally
{
    var a=rot.Angles();
    Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
    foreach(var item in waters) { item.component.Enabled=item.enabled; if(item.enabled)item.component.PrepareViews(); }
}
return new {path,session.HasUnsavedChanges,stages=Enum.GetNames<Sandbox.Rendering.Stage>(),restored=Editor.Mcp.SceneTools.GetEditorCamera()};
