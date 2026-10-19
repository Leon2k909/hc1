var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
var rows=session.Scene.GetAllObjects(true).Where(g=>g.Name.Contains("Dressing")||g.Name=="East"||g.Name=="West").Select(g=>new{
    g.Name,g.Id,g.Enabled,g.Active,Flags=g.Flags.ToString(),Position=g.WorldPosition.ToString(),
    Components=g.Components.GetAll<ModelRenderer>().Select(r=>new{
        r.Enabled,r.Active,Model=r.Model?.ResourcePath,Error=r.Model?.IsError,
        r.RenderType,RenderOptions=r.RenderOptions.ToString(),r.Tint,r.BodyGroups,r.LodOverride,
        Object=r.SceneObject==null?null:new{r.SceneObject.RenderingEnabled,Bounds=r.SceneObject.Bounds.ToString(),r.SceneObject.MeshGroupMask},
        Vertices=r.Model?.GetVertices().Length,Indices=r.Model?.GetIndices().Length
    }).ToArray()
}).ToArray();
var report=new{TimeUtc=DateTime.UtcNow,Game.IsPlaying,ActiveScene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath,session.HasUnsavedChanges,rows};
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"dressing-readback.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
