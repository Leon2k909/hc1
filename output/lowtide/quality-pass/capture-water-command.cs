var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying || session?.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene")throw new Exception("Expected Lowtide edit viewport");
var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var pos=viewport.State.CameraPosition;
var rot=viewport.State.CameraRotation;
var reflection=session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Single();
var enabled=reflection.Enabled;
var camera=Editor.Application.Editor.Camera;
var excluded=camera.RenderExcludeTags.Has("water");
var commands=new Sandbox.Rendering.CommandList("Water draw diagnostic");
var paths=new System.Collections.Generic.List<string>();
try
{
 reflection.Enabled=false;
 camera.RenderExcludeTags.Add("water");
 var water=reflection.GetComponent<ModelRenderer>();
 commands.DrawModel(water.Model,water.WorldTransform);
 foreach(var stage in new[]{Sandbox.Rendering.Stage.AfterSkybox,Sandbox.Rendering.Stage.AfterTransparent})
 {
  camera.AddCommandList(commands,stage,-200);
  Editor.Mcp.SceneTools.SetEditorCamera("-1300,0,125","-2.503,0,0");
  await Task.Delay(250,cancellationToken);
  Editor.Mcp.SceneTools.SetEditorCamera("-1300,0,125","-2.503,0,0");
  using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
  var path=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/water-command-"+stage+".png");
  System.IO.File.WriteAllBytes(path,bitmap.ToPng());
  paths.Add(path);
  camera.RemoveCommandList(commands);
 }
}
finally
{
 camera.RemoveCommandList(commands);
 commands.Reset();
 if(!excluded)camera.RenderExcludeTags.Remove("water");
 else camera.RenderExcludeTags.Add("water");
 // The previous exclusion belonged to the disabled component; let it reacquire ownership.
 if(enabled)camera.RenderExcludeTags.Remove("water");
 var a=rot.Angles();
 Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
 reflection.Enabled=enabled;
 if(enabled)reflection.PrepareViews();
}
return new{paths,session.HasUnsavedChanges};
