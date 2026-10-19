if(Game.IsPlaying)throw new Exception("Stop play for saved-scene verification");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved work");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-response/lighting-reload");
System.IO.Directory.CreateDirectory(folder);
object result=null;
try
{
    session.MakeActive(true);
    await Task.Delay(350,cancellationToken);
    if(Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Wrong viewport");
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var pos=viewport.State.CameraPosition;var rot=viewport.State.CameraRotation;
    try
    {
        var source=ResourceLibrary.Get<SceneFile>("scenes/maps/lowtide/lowtide.scene");
        using(session.Scene.Push())session.Scene.Load(source);
        Editor.Mcp.SceneTools.SetEditorCamera("440,-700,240","12,30,0");
        await Task.Delay(1500,cancellationToken);
        if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
        Editor.Mcp.SceneTools.SetEditorCamera("440,-700,240","12,30,0");
        using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"east-upper.png"),bitmap.ToPng());
        result=new {Source=session.Scene.Source?.ResourcePath,session.HasUnsavedChanges,Volumes=session.Scene.GetAllComponents<IndirectLightVolume>().Select(v=>new {v.GameObject.Name,v.Enabled,v.Active,v.BakeVersion,Path=v.IrradianceTexture?.ResourcePath,Error=v.IrradianceTexture?.IsError}).ToArray()};
    }
    finally
    {
        if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
        {var a=rot.Angles();Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));}
    }
}
finally{if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"readback.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return result;
