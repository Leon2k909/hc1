var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
var renderers=session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_west.vmdl").ToArray();
var materials=new[]{"materials/lowtide/warehouse-floor/lt_warehouse_floor.vmat","materials/lowtide/concrete-wear/lt_concrete_wear.vmat"}.Select(Material.Load).ToArray();
var report=new{TimeUtc=DateTime.UtcNow,Materials=materials.Select(m=>new{m.ResourcePath,m.ShaderName,m.IsError}).ToArray(),
    Renderers=renderers.Select(r=>new{r.GameObject.Name,Model=r.Model.ResourcePath,Slots=r.Model.Materials.Select((m,i)=>new{Index=i,m.ResourcePath,m.ShaderName,m.IsError,Override=r.Materials.GetOverride(i)?.ResourcePath}).Where(m=>m.ResourcePath.Contains("floorboards")||m.ResourcePath.Contains("warehouse_floor")||m.ResourcePath.Contains("lt_concrete")).ToArray()}).ToArray(),
    Game.IsPlaying,ActiveScene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath,session.HasUnsavedChanges};
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-resource-readback.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
