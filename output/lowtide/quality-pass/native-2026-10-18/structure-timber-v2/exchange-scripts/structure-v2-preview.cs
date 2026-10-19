if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2/review");
System.IO.Directory.CreateDirectory(folder);
var timber=Material.Load("materials/lowtide/structure/lt_beam_timber_v2.vmat");
var iron=Material.Load("materials/lowtide/structure/lt_cast_iron_v2.vmat");
if(timber.IsError||iron.IsError||timber.ShaderName!="shaders/hc1_lowtide_structure_v2.shader"||iron.ShaderName!=timber.ShaderName)throw new Exception("Review materials not ready");
var slots=new System.Collections.Generic.List<(ModelRenderer renderer,int index,Material original,Material tuned)>();
foreach(var r in session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_west.vmdl"))
for(int i=0;i<r.Materials.Count;i++)
{
    var path=r.Materials.GetOriginal(i)?.ResourcePath;
    if(path=="materials/lowtide/lt_timber.vmat"||path=="materials/buildings/iron_black.vmat")
        slots.Add((r,i,r.Materials.GetOverride(i),path.Contains("lt_timber")?timber:iron));
}
if(slots.Count!=4||slots.Any(s=>s.original!=null))throw new Exception("Unexpected structure bindings");
var cameras=new[]{
    (name:"east-upper",position:"440,-700,240",angles:"12,30,0"),
    (name:"east-ground",position:"-220,-700,64",angles:"12,18,0"),
    (name:"west-upper",position:"440,700,240",angles:"12,-30,0"),
    (name:"east-column-close",position:"585,-785,250",angles:"-12,45,0"),
    (name:"east-beam-close",position:"650,-700,280",angles:"-40,-90,0"),
    (name:"east-landing",position:"810,-155,72",angles:"15,-60,0")};
var captures=new System.Collections.Generic.List<object>();
void Guard(){if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");}
try
{
    session.MakeActive(true); await Task.Delay(400,cancellationToken);Guard();
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var position=viewport.State.CameraPosition;var rotation=viewport.State.CameraRotation;
    try
    {
        foreach(var camera in cameras)
        foreach(var variant in new[]{"before","tuned"})
        {
            cancellationToken.ThrowIfCancellationRequested();Guard();
            foreach(var slot in slots)
            {
                slot.renderer.Materials.SetOverride(slot.index,variant=="before"?slot.original:slot.tuned);
                slot.renderer.Materials.Apply();
            }
            Editor.Mcp.SceneTools.SetEditorCamera(camera.position,camera.angles);
            await Task.Delay(400,cancellationToken);Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera.position,camera.angles);
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var file=camera.name+"-"+variant+".png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,file),bitmap.ToPng());
            captures.Add(new{file,variant,camera.position,camera.angles});
        }
    }
    finally
    {
        foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.index,slot.original);slot.renderer.Materials.Apply();}
        if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
        {
            var a=rotation.Angles();
            Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{position.x:R},{position.y:R},{position.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
        }
    }
}
finally { if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true); }
var report=new{captures,Slots=slots.Count,OverridesRestored=slots.All(s=>s.renderer.Materials.GetOverride(s.index)==s.original),TabRestored=Editor.SceneEditorSession.Active==previous,session.HasUnsavedChanges,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"capture.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
