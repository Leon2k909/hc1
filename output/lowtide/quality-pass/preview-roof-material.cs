var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying || session?.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene")throw new Exception("Expected Lowtide edit viewport");
var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var pos=viewport.State.CameraPosition;
var rot=viewport.State.CameraRotation;
var material=Material.Load("materials/lowtide/roofs/lt_slate.vmat");
var tint=material.GetVector4("g_flTintColor");
var textures=new[]{"g_tColor","g_tNormal","g_tRoughness"}.Select(x=>new{name=x,texture=material.GetTexture(x)?.ResourcePath}).ToArray();
var results=new System.Collections.Generic.List<string>();
var slots=new System.Collections.Generic.List<(ModelRenderer renderer,int slot,Material original)>();
foreach(var renderer in session.Scene.GetAllComponents<ModelRenderer>())
for(int i=0;i<renderer.Materials.Count;i++)
 if(renderer.Materials.GetOriginal(i)?.ResourcePath==material.ResourcePath)slots.Add((renderer,i,renderer.Materials.GetOverride(i)));
if(slots.Count==0)throw new Exception("No slate material slots");
try
{
 foreach(var candidate in new[]{("roof-material-neutral",new Vector3(.56f,.59f,.62f)),("roof-material-charcoal",new Vector3(.36f,.40f,.45f))})
 {
  var preview=material.CreateCopy(candidate.Item1);
  preview.Set("g_flTintColor",candidate.Item2);
  foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,preview);slot.renderer.Materials.Apply();}
  Editor.Mcp.SceneTools.SetEditorCamera("-1530,-1000,64","-8,-30,0");
  await Task.Delay(250,cancellationToken);
  Editor.Mcp.SceneTools.SetEditorCamera("-1530,-1000,64","-8,-30,0");
  using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
  var path=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass",candidate.Item1+".png");
  System.IO.File.WriteAllBytes(path,bitmap.ToPng());
  results.Add(path);
 }
}
finally
{
 foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,slot.original);slot.renderer.Materials.Apply();}
 var a=rot.Angles();
 Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
}
return new {results,slots=slots.Count,originalTint=tint,textures,material.IsError,session.HasUnsavedChanges};
