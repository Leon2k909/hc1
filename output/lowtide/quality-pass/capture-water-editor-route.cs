var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying || session?.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene")throw new Exception("Expected Lowtide edit viewport");
var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var pos=viewport.State.CameraPosition;
var rot=viewport.State.CameraRotation;
var reflection=session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Single();
var camera=Editor.Application.Editor.Camera;
var owner=session.Scene.Camera;
Sandbox.Rendering.CommandList commands=null;
var path=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/water-editor-route-diagnostic.png");
try
{
 Editor.Mcp.SceneTools.SetEditorCamera("-1300,0,125","-2.503,0,0");
 await Task.Delay(250,cancellationToken);
 Editor.Mcp.SceneTools.SetEditorCamera("-1300,0,125","-2.503,0,0");
 reflection.PrepareViews();
 var views=(System.Collections.IDictionary)reflection.GetType().GetField("views",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).GetValue(reflection);
 var view=views[camera];
 commands=(Sandbox.Rendering.CommandList)view.GetType().GetField("Capture").GetValue(view);
 owner.AddCommandList(commands,Sandbox.Rendering.Stage.AfterSkybox,-200);
 using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
 System.IO.File.WriteAllBytes(path,bitmap.ToPng());
}
finally
{
 if(commands!=null)owner.RemoveCommandList(commands);
 var a=rot.Angles();
 Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
 reflection.PrepareViews();
}
return new{path,owner=owner.GameObject.Name,session.HasUnsavedChanges};
