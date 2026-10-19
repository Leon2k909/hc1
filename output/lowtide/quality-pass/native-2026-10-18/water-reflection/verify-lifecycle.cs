if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var reflection=session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Single();
if(!reflection.Enabled)throw new Exception("Reflection was disabled before review");
var water=reflection.GetComponent<ModelRenderer>();
if(water.Model.Materials.Single().ShaderName!="shaders/hc1_lowtide_water_filtered.shader")throw new Exception("Unexpected production shader");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/water-reflection/production");
System.IO.Directory.CreateDirectory(folder);
var checks=new System.Collections.Generic.List<object>();
int ViewCount()=>((System.Collections.IDictionary)reflection.GetType().GetField("views",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).GetValue(reflection)).Count;
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
        foreach(var state in new[]{("visible","-1300,0,125","-2.503,0,0",1),("outside","12000,10000,256","0,0,0",0),("below","150,0,-160","0,0,0",0),("returned","-1300,0,125","-2.503,0,0",1)})
        {
            Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(state.Item2,state.Item3);
            await Task.Delay(250,cancellationToken);
            Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(state.Item2,state.Item3);
            reflection.PrepareViews();
            int count=ViewCount();
            checks.Add(new{Check=state.Item1,ActiveReflectionViews=count,Expected=state.Item4});
            if(count!=state.Item4)throw new Exception("Reflection lifecycle failed: "+state.Item1);
        }
        reflection.Enabled=false;
        checks.Add(new{Check="disabled",ActiveReflectionViews=ViewCount(),Expected=0});
        if(ViewCount()!=0)throw new Exception("Disabled reflection retained commands");
        reflection.Enabled=true;
        reflection.PrepareViews();
        checks.Add(new{Check="reenabled",ActiveReflectionViews=ViewCount(),Expected=1});
        if(ViewCount()!=1)throw new Exception("Reenabled reflection did not attach");
        foreach(var camera in new[]{("canal","-1300,0,125","-2.503,0,0"),("bank","150,-220,40","28,32,0"),("reverse","1050,0,90","7,180,0")})
        {
            Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            await Task.Delay(350,cancellationToken);
            Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            reflection.PrepareViews();
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,camera.Item1+".png"),bitmap.ToPng());
        }
    }
    finally
    {
        reflection.Enabled=true;
        if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
        {
            var a=rotation.Angles();
            Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{position.x:R},{position.y:R},{position.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
            reflection.PrepareViews();
        }
    }
}
finally
{
    if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
var report=new{TimeUtc=DateTime.UtcNow,checks,TabRestored=Editor.SceneEditorSession.Active==previous,session.HasUnsavedChanges,Game.IsPlaying,reflection.Enabled};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"verification.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
