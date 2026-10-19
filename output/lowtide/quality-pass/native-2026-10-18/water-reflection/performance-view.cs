if(Game.IsPlaying)throw new Exception("Preserve the running match");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/water-reflection");
var action=System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"performance-action.txt")).Trim();
var statePath=System.IO.Path.Combine(folder,"performance-state.json");
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var reflection=session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Single();
string Vec(Vector3 p)=>FormattableString.Invariant($"{p.x:R},{p.y:R},{p.z:R}");
string Rot(Rotation r){var a=r.Angles();return FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}");}
if(action=="setup")
{
    var previous=Editor.SceneEditorSession.Active;
    session.MakeActive(true);
    await Task.Delay(250,cancellationToken);
    if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var state=new{Previous=previous?.Scene.Source?.ResourcePath,Position=Vec(viewport.State.CameraPosition),Angles=Rot(viewport.State.CameraRotation),TargetPosition="-1300,0,125",TargetAngles="-2.503,0,0",SetupUtc=DateTime.UtcNow};
    System.IO.File.WriteAllText(statePath,System.Text.Json.JsonSerializer.Serialize(state,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    Editor.Mcp.SceneTools.SetEditorCamera(state.TargetPosition,state.TargetAngles);
    for(var i=0;i<12;i++)
    {
        await Task.Delay(250,cancellationToken);
        if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed during warmup");
    }
    reflection.PrepareViews();
    return new{State=state,ActualPosition=Vec(viewport.State.CameraPosition),ActualAngles=Rot(viewport.State.CameraRotation),Game.IsPlaying,SampleWindow="Editor viewport only; not a gameplay benchmark"};
}
if(action!="check"&&action!="restore")throw new Exception("Unknown action");
var saved=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(statePath));
if(Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("The user changed the active viewport; leave it untouched");
var view=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var current=new{Position=Vec(view.State.CameraPosition),Angles=Rot(view.State.CameraRotation),TimeUtc=DateTime.UtcNow};
var same=Vector3.DistanceBetween(view.State.CameraPosition,Vector3.Parse(saved["TargetPosition"].GetValue<string>()))<.1f;
var angleMatch=view.State.CameraRotation.Distance(Rotation.From(new Angles(-2.503f,0,0)))<.1f;
if(action=="check")return new{Current=current,PositionMatches=same,AnglesMatch=angleMatch,Game.IsPlaying};
Editor.Mcp.SceneTools.SetEditorCamera(saved["Position"].GetValue<string>(),saved["Angles"].GetValue<string>());
reflection.PrepareViews();
var prior=Editor.SceneEditorSession.All.SingleOrDefault(s=>s.Scene.Source?.ResourcePath==saved["Previous"]?.GetValue<string>());
prior?.MakeActive(true);
return new{Restored=true,Previous=prior?.Scene.Source?.ResourcePath,Current=current,SamplePositionMatched=same,SampleAnglesMatched=angleMatch,Game.IsPlaying,session.HasUnsavedChanges};
