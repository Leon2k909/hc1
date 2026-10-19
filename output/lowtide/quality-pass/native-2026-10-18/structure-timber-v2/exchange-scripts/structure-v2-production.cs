if(Game.IsPlaying)throw new Exception("Preserve play state");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Unsaved Lowtide");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2/production");
System.IO.Directory.CreateDirectory(folder);
var paths=new[]{"materials/lowtide/structure/lt_beam_timber_v2.vmat","materials/lowtide/structure/lt_cast_iron_v2.vmat"};
var renderers=session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_west.vmdl").ToArray();
var bindings=renderers.Select(r=>new {r.Model.ResourcePath,r.Model.IsError,Count=r.Materials.Count,Slots=Enumerable.Range(0,r.Materials.Count).Select(i=>new{Index=i,Path=r.Materials.GetOriginal(i)?.ResourcePath,Shader=r.Materials.GetOriginal(i)?.ShaderName,Error=r.Materials.GetOriginal(i)?.IsError,Override=r.Materials.GetOverride(i)?.ResourcePath}).Where(s=>paths.Contains(s.Path)).ToArray()}).ToArray();
if(bindings.Length!=2||bindings.Any(b=>b.IsError||b.Slots.Length!=2||b.Slots.Any(s=>s.Error!=false||s.Override!=null||s.Shader!="shaders/hc1_lowtide_structure_v2.shader")))throw new Exception("Production bindings are not ready: "+System.Text.Json.JsonSerializer.Serialize(bindings));
var cameras=new[]{(name:"east-upper",position:"440,-700,240",angles:"12,30,0"),(name:"east-ground",position:"-220,-700,64",angles:"12,18,0"),(name:"west-upper",position:"440,700,240",angles:"12,-30,0"),(name:"east-column-close",position:"585,-785,250",angles:"-12,45,0"),(name:"east-beam-close",position:"650,-700,280",angles:"-40,-90,0"),(name:"east-landing",position:"810,-155,72",angles:"15,-60,0")};
void Guard(){if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");}
try
{
    session.MakeActive(true);await Task.Delay(400,cancellationToken);Guard();
    var view=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;var pos=view.State.CameraPosition;var rot=view.State.CameraRotation;
    try
    {
        foreach(var camera in cameras)
        {
            cancellationToken.ThrowIfCancellationRequested();Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera.position,camera.angles);await Task.Delay(400,cancellationToken);Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera.position,camera.angles);
            using var bmp=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,camera.name+".png"),bmp.ToPng());
        }
    }
    finally{if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session){var a=rot.Angles();Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));}}
}
finally{if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session)previous?.MakeActive(true);}
var report=new{bindings,Captures=cameras.Select(c=>c.name+".png").ToArray(),session.HasUnsavedChanges,TabRestored=Editor.SceneEditorSession.Active==previous,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"verification.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
