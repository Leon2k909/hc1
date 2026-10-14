var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying || session?.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene" || session.HasUnsavedChanges) throw new Exception("Expected saved Lowtide editor");
var scene=session.Scene;
var tone=scene.GetAllComponents<Tonemapping>().Single();
var fog=scene.GetAllComponents<GradientFog>().Single();
var oldMode=tone.Mode;
var oldStart=fog.StartDistance;
var oldEnd=fog.EndDistance;
var oldFalloff=fog.FalloffExponent;
var oldComp=tone.ExposureCompensation;
var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var pos=viewport.State.CameraPosition;
var rot=viewport.State.CameraRotation;
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass");
var results=new System.Collections.Generic.List<string>();
try
{
 foreach(var treatment in new[]{"current","atmosphere"})
 {
  tone.Mode=treatment=="current"?oldMode:Tonemapping.TonemappingMode.AgX;
  tone.ExposureCompensation=treatment=="current"?oldComp:-.1f;
  fog.StartDistance=treatment=="current"?oldStart:600;
  fog.EndDistance=treatment=="current"?oldEnd:16000;
  fog.FalloffExponent=treatment=="current"?oldFalloff:1.45f;
  foreach(var view in new[]{("quay","-1530,-1000,64","-8,-30,0"),("canal","-1533.12781,-199.585312,214.872894","15.4000359,7.20221281,0")})
  {
   cancellationToken.ThrowIfCancellationRequested();
   Editor.Mcp.SceneTools.SetEditorCamera(view.Item2,view.Item3);
   await Task.Delay(300,cancellationToken);
   Editor.Mcp.SceneTools.SetEditorCamera(view.Item2,view.Item3);
   using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
   var path=System.IO.Path.Combine(folder,"tone-preview-"+treatment+"-"+view.Item1+".png");
   System.IO.File.WriteAllBytes(path,bitmap.ToPng());results.Add(path);
  }
 }
}
finally
{
 tone.Mode=oldMode;tone.ExposureCompensation=oldComp;
 fog.StartDistance=oldStart;fog.EndDistance=oldEnd;fog.FalloffExponent=oldFalloff;
 var a=rot.Angles();
 Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
}
return new {results,restored=new{tone.Mode,tone.ExposureCompensation,fog.StartDistance,fog.EndDistance,fog.FalloffExponent},session.HasUnsavedChanges};
