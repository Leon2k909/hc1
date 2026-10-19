var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
var ids=new[]{"281f4421-6de1-88fd-b149-c6e878de6c38","389d528c-7686-80f2-a81f-7e1cc1a0e5e3","4975211e-b1c2-8cef-a473-955b34357d54","c07a7104-a0f9-854a-b996-95a41b620b0b"};
var objects=session.Scene.GetAllObjects(true).Where(x=>ids.Contains(x.Id.ToString())).Select(x=>new {Id=x.Id.ToString(),x.Name,Parent=x.Parent?.Name}).ToArray();
var components=session.Scene.GetAllComponents<Component>().Where(x=>ids.Contains(x.Id.ToString())).Select(x=>new{Id=x.Id.ToString(),Type=x.GetType().FullName,Object=x.GameObject.Name}).ToArray();
var data=new {session.HasUnsavedChanges,objects,components};
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current/lighting/prefab-cache-readback.json"),System.Text.Json.JsonSerializer.Serialize(data,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return data;
