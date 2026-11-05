var session = Editor.SceneEditorSession.All.Single(x => x.Scene.Name == "sewage");
var renderer = session.Scene.GetAllObjects(true).Single(x=>x.Id==Guid.Parse("2a628f77-20cc-59ba-9a1d-db7628c9c7ba")).Components.Get<ModelRenderer>();
if (renderer.MaterialOverride?.ResourcePath != "materials/sewage/pipe-texture-v1/pipe.vmat" || renderer.MaterialOverride.IsError) throw new Exception("Pipe material verification failed.");
session.Save(false);
return new { Saved=!session.HasUnsavedChanges, Scene=session.Scene.Name, Material=renderer.MaterialOverride.ResourcePath, ActiveScene=Editor.SceneEditorSession.Active.Scene.Name, Game.IsPlaying };
