if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previousPath=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/paving-before-open.json")))["result"]["ActiveScenePath"].GetValue<string>();
var previous=Editor.SceneEditorSession.All.FirstOrDefault(s=>s.Scene.Source?.ResourcePath==previousPath);
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(Editor.SceneEditorSession.Active!=session)throw new Exception("User changed tabs after opening Lowtide");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/paving-contact");
System.IO.Directory.CreateDirectory(System.IO.Path.Combine(folder,"review"));
var candidate=Material.Load("materials/lowtide/paving-use/lt_setts_review.vmat");
if(candidate.IsError||candidate.GetTexture("g_tPavingUse")?.Width!=2048)throw new Exception("Candidate not compiled and bound");
var slots=new System.Collections.Generic.List<(ModelRenderer renderer,int index,Material previous)>();
foreach(var r in session.Scene.GetAllComponents<ModelRenderer>())
for(int i=0;i<r.Materials.Count;i++)
    if(r.Materials.GetOriginal(i)?.ResourcePath=="materials/lowtide/lt_setts.vmat")slots.Add((r,i,r.Materials.GetOverride(i)));
if(slots.Count==0)throw new Exception("No paving slots");
var cameras=new[]{("pipe-outlet","230,-1060,30","17.566221,113.860175,0"),
    ("shed-foot","-1125,-1290,28","21.56,-20.56,0"),
    ("warehouse-player","260,-1110,64","29.88,119.42,0"),
    ("west-player","260,1110,64","29.88,-119.42,0"),
    ("street-distance","-250,-1200,64","8,19.983107,0")};
var captures=new System.Collections.Generic.List<string>();
try
{
    session.MakeActive(true);
    await Task.Delay(400,cancellationToken);
    if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var position=viewport.State.CameraPosition;var rotation=viewport.State.CameraRotation;
    try
    {
        foreach(var camera in cameras)
        foreach(var use in new[]{false,true})
        {
            cancellationToken.ThrowIfCancellationRequested();
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.index,use?candidate:slot.previous);slot.renderer.Materials.Apply();}
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            await Task.Delay(400,cancellationToken);
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var name=camera.Item1+(use?"-candidate":"-before")+".png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"review",name),bitmap.ToPng());captures.Add(name);
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
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"review/capture.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
