var report=new {
    TimeUtc=DateTime.UtcNow, Game.IsPlaying,
    Runtime=Game.ActiveScene?.Source?.ResourcePath,
    Active=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath,
    Sessions=Editor.SceneEditorSession.All.Select(s=>new {Path=s.Scene.Source?.ResourcePath,s.Scene.IsEditor,s.HasUnsavedChanges,Active=s==Editor.SceneEditorSession.Active}).ToArray()
};
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2");
System.IO.Directory.CreateDirectory(folder);
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"state-before.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
