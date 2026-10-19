if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
var request=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"capture-request.json")));
var output=System.IO.Path.Combine(folder,request["folder"].GetValue<string>());
System.IO.Directory.CreateDirectory(output);
var timber=Material.Load("materials/lowtide/warehouse-floor/lt_warehouse_floor.vmat");
var concrete=Material.Load("materials/lowtide/concrete-wear/lt_concrete_wear.vmat");
if(timber.IsError||timber.ShaderName!="shaders/hc1_lowtide_warehouse_floor.shader"||concrete.IsError||concrete.ShaderName!="shaders/hc1_lowtide_concrete_wear.shader")throw new Exception("Candidate materials are not ready");
var slots=new System.Collections.Generic.List<(ModelRenderer renderer,int index,Material previous,Material candidate)>();
foreach(var r in session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_west.vmdl"))
for(int i=0;i<r.Materials.Count;i++)
{
    var path=r.Materials.GetOriginal(i)?.ResourcePath;
    if(path=="materials/buildings/floorboards.vmat"||path=="materials/lowtide/interior/lt_concrete.vmat")
        slots.Add((r,i,r.Materials.GetOverride(i),path.Contains("floorboards")?timber:concrete));
}
if(slots.Count!=4||slots.Any(s=>s.previous!=null))throw new Exception("Unexpected floor bindings or overrides");
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
        foreach(var camera in request["cameras"].AsArray())
        foreach(var use in new[]{false,true})
        {
            cancellationToken.ThrowIfCancellationRequested();Guard();
            foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.index,use?slot.candidate:slot.previous);slot.renderer.Materials.Apply();}
            Editor.Mcp.SceneTools.SetEditorCamera(camera["position"].GetValue<string>(),camera["angles"].GetValue<string>());
            await Task.Delay(350,cancellationToken);
            Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera["position"].GetValue<string>(),camera["angles"].GetValue<string>());
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var name=camera["name"].GetValue<string>()+(use?"-candidate":"-before")+".png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,name),bitmap.ToPng());
            captures.Add(new{name,Candidate=use,Position=camera["position"].GetValue<string>(),Angles=camera["angles"].GetValue<string>()});
        }
    }
    finally
    {
        foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.index,slot.previous);slot.renderer.Materials.Apply();}
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
var report=new{captures,Slots=slots.Count,OverridesRestored=slots.All(s=>s.renderer.Materials.GetOverride(s.index)==s.previous),TabRestored=Editor.SceneEditorSession.Active==previous,session.HasUnsavedChanges,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(output,"capture.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
