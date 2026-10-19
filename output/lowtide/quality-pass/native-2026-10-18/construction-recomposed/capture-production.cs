if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/construction-recomposed");
var requests=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"native-review/views.json"))).AsArray();
var selected=new[]{"east-window","east-door","shed-hopper","pipe-outlet","canal-wide"};
System.IO.Directory.CreateDirectory(System.IO.Path.Combine(folder,"production-review"));
var captures=new System.Collections.Generic.List<string>();
object record=null;
try
{
    session.MakeActive(true);
    await Task.Delay(350,cancellationToken);
    if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var position=viewport.State.CameraPosition;var rotation=viewport.State.CameraRotation;
    try
    {
        foreach(var request in requests.Where(r=>selected.Contains(r["name"].GetValue<string>())))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            var p=request["position"].GetValue<string>();var a=request["angles"].GetValue<string>();
            Editor.Mcp.SceneTools.SetEditorCamera(p,a);
            await Task.Delay(450,cancellationToken);
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            Editor.Mcp.SceneTools.SetEditorCamera(p,a);
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var name=request["name"].GetValue<string>()+".png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"production-review",name),bitmap.ToPng());
            captures.Add(name);
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
    var renderers=session.Scene.GetAllComponents<ModelRenderer>().ToArray();
    var modelErrors=renderers.Where(r=>r.Model==null||r.Model.IsError).Select(r=>r.GameObject.Name).ToArray();
    var materialErrors=renderers.SelectMany(r=>Enumerable.Range(0,r.Materials.Count).Where(i=>r.Materials.GetOriginal(i)?.IsError==true).Select(i=>r.GameObject.Name+":"+i)).ToArray();
    record=new{captures,modelErrors,materialErrors,session.HasUnsavedChanges,Game.IsPlaying,restoreTab=previous?.Scene.Source?.ResourcePath,TimeUtc=DateTime.UtcNow};
}
finally
{
    if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
var report=new{capture=record,TabRestored=Editor.SceneEditorSession.Active==previous,Game.IsPlaying};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-review/capture.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
