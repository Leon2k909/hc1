var material=Material.Load("materials/lowtide/water-review/lt_water_filter_review.vmat");
var model=Model.Load("models/maps/lowtide/lowtide_water_filter_review.vmdl");
var report=new{
    TimeUtc=DateTime.UtcNow,Game.IsPlaying,
    RuntimeScene=Game.ActiveScene?.Source?.ResourcePath,
    EditorScene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath,
    Scenes=Editor.SceneEditorSession.All.Select(s=>new{Path=s.Scene.Source?.ResourcePath,s.HasUnsavedChanges}).ToArray(),
    Material=new{material.ResourcePath,material.ShaderName,material.IsError},
    Model=new{model.ResourcePath,model.IsError,Materials=model.Materials.Select(m=>new{m.ResourcePath,m.ShaderName,m.IsError}).ToArray()}
};
var file=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/water-reflection/review-readback.json");
System.IO.File.WriteAllText(file,System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
