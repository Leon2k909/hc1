var remaining = Scene.All.Where(s => s.IsValid() && s.GetAllComponents<CameraComponent>()
    .Any(c => c.GameObject.Name == "Lowtide finish QA camera")).Select(s => s.Name).ToArray();
var result = new { remainingQaScenes = remaining };
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),
    "output/lowtide/quality-pass/window-cleanup-check.json"),
    System.Text.Json.JsonSerializer.Serialize(result));
return result;
