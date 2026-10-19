if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/water-reflection");
var phase=System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"capture-phase.txt")).Trim();
if(phase!="baseline"&&phase!="comparison")throw new Exception("Unknown phase");
System.IO.Directory.CreateDirectory(System.IO.Path.Combine(folder,phase));
var reflection=session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Single();
var water=reflection.GetComponent<ModelRenderer>();
var original=water.Model;
var candidate=phase=="comparison"?Model.Load("models/maps/lowtide/lowtide_water_filter_review.vmdl"):original;
if(candidate.IsError)throw new Exception("Review model failed");
var records=new System.Collections.Generic.List<object>();
try
{
    session.MakeActive(true);
    await Task.Delay(350,cancellationToken);
    if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var position=viewport.State.CameraPosition;var rotation=viewport.State.CameraRotation;
    try
    {
        foreach(var camera in new[]{("canal","-1300,0,125","-2.503,0,0"),("bank","150,-220,40","28,32,0"),("reverse","1050,0,90","7,180,0")})
        foreach(var use in phase=="comparison"?new[]{false,true}:new[]{false})
        {
            cancellationToken.ThrowIfCancellationRequested();
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            water.Model=use?candidate:original;
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            await Task.Delay(400,cancellationToken);
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            reflection.PrepareViews();
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var name=camera.Item1+(use?"-filtered":"-current")+".png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,phase,name),bitmap.ToPng());
            var views=(System.Collections.IDictionary)reflection.GetType().GetField("views",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).GetValue(reflection);
            records.Add(new{name,Filtered=use,ActiveReflectionViews=views.Count,Materials=water.Model.Materials.Select(m=>new{m.ResourcePath,m.ShaderName,m.IsError}).ToArray()});
        }
    }
    finally
    {
        water.Model=original;
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
var report=new{phase,records,ModelRestored=water.Model==original,TabRestored=Editor.SceneEditorSession.Active==previous,session.HasUnsavedChanges,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,phase,"capture.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
