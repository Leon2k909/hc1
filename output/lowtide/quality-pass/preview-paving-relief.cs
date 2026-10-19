var session=Editor.SceneEditorSession.Active;
var view=Editor.SceneViewWidget.Current;
if(Game.IsPlaying || session?.Scene?.IsEditor!=true || session.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene" || session.HasUnsavedChanges || view?.Session!=session)
 throw new Exception("Expected clean, active Lowtide editor viewport; never redirect the runtime camera");
var viewport=view.LastSelectedViewportWidget;
if(viewport?.Renderer?.Camera==null)throw new Exception("No existing editor camera");
var pos=viewport.State.CameraPosition;
var rot=viewport.State.CameraRotation;
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass");
var candidate=Material.Load("materials/lowtide/paving_relief/lt_setts_relief.vmat");
if(candidate.IsError || candidate.GetTexture("g_tHeight")?.Width!=2048)throw new Exception("Candidate is not compiled and bound");
var slots=new System.Collections.Generic.List<(ModelRenderer renderer,int slot,Material original)>();
foreach(var renderer in session.Scene.GetAllComponents<ModelRenderer>())
for(int i=0;i<renderer.Materials.Count;i++)
 if(renderer.Materials.GetOriginal(i)?.ResourcePath=="materials/lowtide/lt_setts.vmat")
  slots.Add((renderer,i,renderer.Materials.GetOverride(i)));
if(slots.Count==0)throw new Exception("No paving slots");
var results=new System.Collections.Generic.List<object>();
try
{
 foreach(var camera in new[]{("quay","-1530,-1000,64","-8,-30,0"),
                            ("close","-1530,-1000,64","52,-30,0"),
                            ("grazing","-1530,-1000,64","12,-30,0"),
                            ("west","-1530,1000,64","38,30,0")})
 foreach(var useCandidate in new[]{false,true})
 {
  if(Game.IsPlaying || Editor.SceneEditorSession.Active!=session || Editor.SceneViewWidget.Current?.Session!=session)
   throw new Exception("Editor state changed during comparison");
  foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,useCandidate?candidate:slot.original);slot.renderer.Materials.Apply();}
  Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
  await Task.Delay(250,cancellationToken);
  cancellationToken.ThrowIfCancellationRequested();
  if(Game.IsPlaying || Editor.SceneEditorSession.Active!=session)throw new Exception("Play state changed during capture");
  Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
  using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
  var name="paving-relief-"+camera.Item1+(useCandidate?"-candidate":"-before")+".png";
  System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,name),bitmap.ToPng());
  results.Add(new{name,position=camera.Item2,angles=camera.Item3,candidate=useCandidate});
 }
}
finally
{
 foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,slot.original);slot.renderer.Materials.Apply();}
 if(!Game.IsPlaying && Editor.SceneEditorSession.Active==session && Editor.SceneViewWidget.Current?.Session==session)
 {
  var a=rot.Angles();
  Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
 }
}
var restored=slots.All(slot=>slot.renderer.Materials.GetOverride(slot.slot)==slot.original);
var report=new{results,slots=slots.Count,restored,session.HasUnsavedChanges,Game.IsPlaying,originalPosition=pos,originalRotation=rot};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"paving-relief-preview.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
