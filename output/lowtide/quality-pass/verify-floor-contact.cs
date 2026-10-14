var folder = System.IO.Path.Combine(Project.Current.GetRootPath(), "output/lowtide/quality-pass");
var material = Material.Load("materials/lowtide/interior/lt_concrete.vmat");
var texture = material.GetTexture("g_tFloorContact");
if (texture is null || texture.Width != 768 || texture.Height != 768) throw new Exception("Floor contact texture is not bound correctly");
var remaining = Scene.All.Where(s => s.IsValid() && s.GetAllComponents<CameraComponent>().Any(c => c.GameObject.Name == "Lowtide finish QA camera")).Select(s => s.Name).ToArray();
if (remaining.Length != 0) throw new Exception("QA preview is still alive");
var result = new { textureBound = true, texture.Width, texture.Height, materialError=material.IsError, remainingQaScenes=remaining, activeEditorScene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath, activeGameScene=Game.ActiveScene?.Name };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "floor-contact-engine-checks.json"), System.Text.Json.JsonSerializer.Serialize(result));
return result;
