if(Game.IsPlaying)throw new Exception("Preserve the running game; compare in edit mode");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved edits");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/container-surface");
var sourcePrefix="materials/lowtide/containers/lt_container_";
var slots=new System.Collections.Generic.List<(ModelRenderer renderer,int slot,Material original,Material candidate)>();
var bindingChecks=new System.Collections.Generic.List<object>();
foreach(var renderer in session.Scene.GetAllComponents<ModelRenderer>())
for(int i=0;i<renderer.Materials.Count;i++)
{
 var path=renderer.Materials.GetOriginal(i)?.ResourcePath;
 if(path?.StartsWith(sourcePrefix)!=true)continue;
 var candidatePath=path.Replace("/containers/","/container_surface/");
 var material=Material.Load(candidatePath);
 var textures=new[]{"g_tColor","g_tNormal","g_tRma"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray();
 if(material.IsError||textures.Any(x=>x.width!=2048||x.height!=2048))throw new Exception("Candidate binding not ready: "+candidatePath);
 slots.Add((renderer,i,renderer.Materials.GetOverride(i),material));
 bindingChecks.Add(new{candidatePath,textures,roughness=material.GetVector4("g_flCoatRoughness"),weathering=material.GetVector4("g_flWeathering")});
}
if(slots.Count!=8)throw new Exception("Expected eight original panel/frame slots, got "+slots.Count);
var captures=new System.Collections.Generic.List<object>();
object cameraAfter=null;
try
{
 session.MakeActive(true);
 await Task.Delay(250,cancellationToken);
 if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport did not activate");
 var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
 var pos=viewport.State.CameraPosition;
 var rot=viewport.State.CameraRotation;
 try
 {
  foreach(var camera in new[]{("quay","-1530,-1000,64","-8,-30,0"),("blue","-1435,-1370,64","4,-34,0"),
                             ("corner","-1355,-1325,90","-3,-39,0"),("red","-1435,1370,64","4,34,0")})
  foreach(var candidate in new[]{false,true})
  {
   cancellationToken.ThrowIfCancellationRequested();
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,candidate?slot.candidate:slot.original);slot.renderer.Materials.Apply();}
   Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
   await Task.Delay(1200,cancellationToken);
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
   using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
   var name=camera.Item1+(candidate?"-candidate":"-before")+".png";
   System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,name),bitmap.ToPng());
   captures.Add(new{name,position=camera.Item2,angles=camera.Item3,candidate});
  }
 }
 finally
 {
  foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,slot.original);slot.renderer.Materials.Apply();}
  if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
  {
   var a=rot.Angles();
   Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
   cameraAfter=Editor.Mcp.SceneTools.GetEditorCamera();
  }
 }
 var report=new{captures,bindingChecks,slots=slots.Count,overridesRestored=slots.All(s=>s.renderer.Materials.GetOverride(s.slot)==s.original),session.HasUnsavedChanges,Game.IsPlaying,cameraAfter,restoreTab=previous?.Scene.Source?.ResourcePath};
 System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-preview.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
 return report;
}
finally
{
 if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
