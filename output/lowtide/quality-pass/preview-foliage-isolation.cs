if(Game.IsPlaying)throw new Exception("Preserve the running game");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved edits");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/foliage");
var original=Material.Load("models/sbox_props/trees/oak/oak_branch.vmat");
var compiled=Material.Load("materials/lowtide/foliage/lt_oak_branch.vmat");
var candidate=original.CreateCopy();
candidate.Set("g_tColor",compiled.GetTexture("g_tColor"));
if(candidate.IsError||candidate.GetTexture("g_tColor")?.Width!=1254)throw new Exception("Private candidate is not ready");
var slots=new System.Collections.Generic.List<(ModelRenderer renderer,int slot,Material previous)>();
foreach(var renderer in session.Scene.GetAllComponents<ModelRenderer>())
for(int i=0;i<renderer.Materials.Count;i++)
 if(renderer.Materials.GetOriginal(i)?.ResourcePath==original.ResourcePath)slots.Add((renderer,i,renderer.Materials.GetOverride(i)));
if(slots.Count!=4)throw new Exception("Expected four leaf slots");
var captures=new System.Collections.Generic.List<string>();
object cameraBefore=null,cameraAfter=null;
try
{
 session.MakeActive(true);
 await Task.Delay(250,cancellationToken);
 if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport did not activate");
 var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
 var pos=viewport.State.CameraPosition;
 var rot=viewport.State.CameraRotation;
 cameraBefore=Editor.Mcp.SceneTools.GetEditorCamera();
 try
 {
  foreach(var camera in new[]{("quay","-1530,-1000,64","-8,-30,0"),("crown","-930,-1200,220","-20,-26.565,0"),("west","-930,1200,220","-20,26.565,0")})
  foreach(var useCandidate in new[]{false,true})
  {
   cancellationToken.ThrowIfCancellationRequested();
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,useCandidate?candidate:slot.previous);slot.renderer.Materials.Apply();}
   Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
   await Task.Delay(1500,cancellationToken);
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
   using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
   var name=camera.Item1+(useCandidate?"-albedo-only":"-isolation-before")+".png";
   System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,name),bitmap.ToPng());
   captures.Add(name);
  }
 }
 finally
 {
  foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,slot.previous);slot.renderer.Materials.Apply();}
  if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
  {
   var a=rot.Angles();
   Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
   cameraAfter=Editor.Mcp.SceneTools.GetEditorCamera();
  }
 }
 var report=new{candidate=candidate.ResourcePath,captures,slots=slots.Count,overridesRestored=slots.All(s=>s.renderer.Materials.GetOverride(s.slot)==s.previous),cameraBefore,cameraAfter,restoreTab=previous?.Scene.Source?.ResourcePath,session.HasUnsavedChanges,Game.IsPlaying};
 System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"isolation-preview.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
 return report;
}
finally
{
 if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
