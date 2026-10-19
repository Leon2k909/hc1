if(Game.IsPlaying)throw new Exception("Do not redirect a runtime view");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide is dirty");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass");
var requests=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"viewport-request.json"))).AsArray();
var captures=new System.Collections.Generic.List<string>();
object cameraAfter=null;
try
{
 session.MakeActive(true);
 await Task.Delay(250,cancellationToken);
 if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Native viewport did not activate");
 var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
 var pos=viewport.State.CameraPosition;
 var rot=viewport.State.CameraRotation;
 try
 {
  foreach(var request in requests)
  {
   cancellationToken.ThrowIfCancellationRequested();
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   Editor.Mcp.SceneTools.SetEditorCamera(request["position"].GetValue<string>(),request["angles"].GetValue<string>());
   await Task.Delay(1200,cancellationToken);
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   Editor.Mcp.SceneTools.SetEditorCamera(request["position"].GetValue<string>(),request["angles"].GetValue<string>());
   using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
   var name=request["name"].GetValue<string>()+".png";
   if(System.IO.Path.GetFileName(name)!=name)throw new Exception("Unexpected capture path");
   System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,name),bitmap.ToPng());
   captures.Add(name);
  }
 }
 finally
 {
  if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
  {
   var a=rot.Angles();
   Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
   cameraAfter=Editor.Mcp.SceneTools.GetEditorCamera();
  }
 }
 var renderers=session.Scene.GetAllComponents<ModelRenderer>().ToArray();
 var modelErrors=renderers.Where(r=>r.Model==null||r.Model.IsError).Select(r=>r.GameObject.Name).ToArray();
 var materialErrors=renderers.SelectMany(r=>Enumerable.Range(0,r.Materials.Count).Where(i=>r.Materials.GetOriginal(i)?.IsError==true).Select(i=>r.GameObject.Name+":"+i)).ToArray();
 var sourceHashes=new System.Collections.Generic.Dictionary<string,string>();
 foreach(var side in new[]{"east","west"})
 {
  var relative="models/maps/lowtide/lowtide_dress_"+side+".obj";
  var data=System.IO.File.ReadAllBytes(System.IO.Path.Combine(Project.Current.GetRootPath(),"Assets",relative));
  sourceHashes[relative]=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(data)).ToLowerInvariant();
 }
 var report=new{captures,sourceHashes,modelErrors,materialErrors,session.HasUnsavedChanges,Game.IsPlaying,cameraAfter,restoreTab=previous?.Scene.Source?.ResourcePath,previousTabDirty=previous?.HasUnsavedChanges};
 System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"container-detail/native-verify.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
 return report;
}
finally
{
 if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
