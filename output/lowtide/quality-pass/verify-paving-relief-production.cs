var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var session=Editor.SceneEditorSession.Active;
var view=Editor.SceneViewWidget.Current;
if(Game.IsPlaying || session?.Scene?.IsEditor!=true || session.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene" || session.HasUnsavedChanges || view?.Session!=session)
 throw new Exception("Expected clean Lowtide edit viewport");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"paving-relief-production-manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())throw new Exception("Protected source changed: "+item.Key);
foreach(var item in manifest["changes"].AsObject())
 if(Hash(System.IO.Path.Combine(root,"Assets",item.Key))!=item.Value["after"].GetValue<string>())throw new Exception("Production material differs");
var material=Material.Load("materials/lowtide/lt_setts.vmat");
var textures=new[]{"g_tColor","g_tNormal","g_tRma","g_tHeight"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray();
if(material.IsError||textures.Any(x=>x.width!=2048||x.height!=2048))throw new Exception("Invalid production texture binding");
var slots=session.Scene.GetAllComponents<ModelRenderer>().SelectMany(renderer=>Enumerable.Range(0,renderer.Materials.Count)
 .Where(i=>renderer.Materials.GetOriginal(i)?.ResourcePath==material.ResourcePath)
 .Select(i=>new{name=renderer.GameObject.Name,index=i,hasOverride=renderer.Materials.GetOverride(i)!=null})).ToArray();
if(slots.Length!=3||slots.Any(x=>x.hasOverride))throw new Exception("Unexpected production paving slots");
var viewport=view.LastSelectedViewportWidget;
if(viewport?.Renderer?.Camera==null)throw new Exception("No existing editor camera");
var pos=viewport.State.CameraPosition;
var rot=viewport.State.CameraRotation;
var captures=new System.Collections.Generic.List<object>();
try
{
 foreach(var camera in new[]{("quay","-1530,-1000,64","-8,-30,0"),("close","-1530,-1000,64","52,-30,0"),
                            ("grazing","-1530,-1000,64","12,-30,0"),("west","-1530,1000,64","38,30,0")})
 {
  if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport state changed");
  Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
  await Task.Delay(250,cancellationToken);
  cancellationToken.ThrowIfCancellationRequested();
  if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport state changed");
  Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
  using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1280,720);
  var name="paving-relief-"+camera.Item1+"-production.png";
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
 }
}
var report=new{material.IsError,textures,slots,depth=material.GetVector4("g_flReliefDepth"),scale=material.GetVector4("g_vPavingScale"),region=material.GetVector4("g_vPavingRegion"),
 protectedFiles=manifest["protected"].AsObject().Count,captures,session.HasUnsavedChanges,Game.IsPlaying,originalPosition=pos,originalRotation=rot,restoredCamera=Editor.Mcp.SceneTools.GetEditorCamera()};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"paving-relief-production-verification.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
