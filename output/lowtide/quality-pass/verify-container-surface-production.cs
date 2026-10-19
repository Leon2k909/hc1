if(Game.IsPlaying)throw new Exception("Preserve the running game");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/container-surface");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"production-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
var materialHashes=new System.Collections.Generic.Dictionary<string,string>();
var bindingChecks=new System.Collections.Generic.List<object>();
foreach(var item in manifest["changes"].AsObject())
{
 var hash=Hash(System.IO.Path.Combine(root,"Assets",item.Key));
 if(hash!=item.Value["after"].GetValue<string>())throw new Exception("Production material changed: "+item.Key);
 materialHashes[item.Key]=hash;
 var material=Material.Load(item.Key);
 var textures=new[]{"g_tColor","g_tNormal","g_tRma"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray();
 var roughness=material.GetVector4("g_flCoatRoughness");
 var weathering=material.GetVector4("g_flWeathering");
 var rail=material.GetVector4("g_flIsRail");
 if(material.IsError||textures.Any(x=>x.width!=2048||x.height!=2048)||MathF.Abs(roughness.x-.74f)>.001f||MathF.Abs(weathering.x-.85f)>.001f||MathF.Abs(rail.x-(item.Key.Contains("_frame.")?1:0))>.001f)throw new Exception("Production binding not ready: "+item.Key);
 bindingChecks.Add(new{path=item.Key,textures,roughness,weathering,rail});
}
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved edits");
var slots=new System.Collections.Generic.List<object>();
foreach(var renderer in session.Scene.GetAllComponents<ModelRenderer>())
for(int i=0;i<renderer.Materials.Count;i++)
{
 var material=renderer.Materials.GetOriginal(i);
 if(material?.ResourcePath?.StartsWith("materials/lowtide/containers/lt_container_")!=true)continue;
 if(renderer.Materials.GetOverride(i)!=null||material.IsError||MathF.Abs(material.GetVector4("g_flCoatRoughness").x-.74f)>.001f)throw new Exception("Unexpected override or stale slot: "+renderer.GameObject.Name);
 slots.Add(new{renderer=renderer.GameObject.Name,slot=i,path=material.ResourcePath});
}
if(slots.Count!=8)throw new Exception("Expected eight production container slots");
var captures=new System.Collections.Generic.List<object>();
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
  foreach(var camera in new[]{("quay","-1530,-1000,64","-8,-30,0"),("blue","-1435,-1370,64","4,-34,0"),("corner","-1355,-1325,90","-3,-39,0"),("red","-1435,1370,64","4,34,0")})
  {
   cancellationToken.ThrowIfCancellationRequested();
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
   await Task.Delay(1500,cancellationToken);
   if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
   Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
   using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
   var name=camera.Item1+"-production.png";
   System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,name),bitmap.ToPng());
   captures.Add(new{name,position=camera.Item2,angles=camera.Item3});
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
 var report=new{captures,materialHashes,bindingChecks,slots,modelErrors,materialErrors,session.HasUnsavedChanges,Game.IsPlaying,cameraBefore,cameraAfter,restoreTab=previous?.Scene.Source?.ResourcePath};
 System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-native-verify.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
 return new{materials=bindingChecks.Count,slots=slots.Count,captures=captures.Count,modelErrors,materialErrors,session.HasUnsavedChanges,Game.IsPlaying};
}
finally
{
 if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
