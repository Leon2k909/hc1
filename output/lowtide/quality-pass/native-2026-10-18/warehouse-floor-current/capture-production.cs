if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
var request=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"capture-request.json")));
var output=System.IO.Path.Combine(folder,"production");
System.IO.Directory.CreateDirectory(output);
var renderers=session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_west.vmdl").ToArray();
foreach(var r in renderers)
{
    if(r.Model.Materials.Count(m=>m.ResourcePath=="materials/lowtide/warehouse-floor/lt_warehouse_floor.vmat"||m.ResourcePath=="materials/lowtide/concrete-wear/lt_concrete_wear.vmat")!=2)throw new Exception("Production bindings not ready");
    for(int i=0;i<r.Materials.Count;i++)if(r.Materials.GetOverride(i)!=null)throw new Exception("Unexpected renderer override");
}
var captures=new System.Collections.Generic.List<object>();
void Guard(){if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");}
try
{
    session.MakeActive(true);
    await Task.Delay(350,cancellationToken);
    Guard();
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var position=viewport.State.CameraPosition;var rotation=viewport.State.CameraRotation;
    try
    {
        foreach(var camera in request["cameras"].AsArray().Where(c=>c["name"].GetValue<string>().Contains("player")||c["name"].GetValue<string>().Contains("timber-close")))
        {
            cancellationToken.ThrowIfCancellationRequested();Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera["position"].GetValue<string>(),camera["angles"].GetValue<string>());
            await Task.Delay(350,cancellationToken);
            Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera["position"].GetValue<string>(),camera["angles"].GetValue<string>());
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var name=camera["name"].GetValue<string>()+".png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,name),bitmap.ToPng());
            captures.Add(new{name,Position=viewport.State.CameraPosition.ToString(),Angles=viewport.State.CameraRotation.Angles().ToString()});
        }
    }
    finally
    {
        if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
        {
            var a=rotation.Angles();
            Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{position.x:R},{position.y:R},{position.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
        }
    }
}
finally
{
    if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
var report=new{captures,TabRestored=Editor.SceneEditorSession.Active==previous,session.HasUnsavedChanges,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(output,"capture.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
