
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var m = s.Scene.Camera;
m.FieldOfView = 60f;
await Task.Delay( 200 );
return new { Obj = m.GameObject.Name, Fov = m.FieldOfView, Pos = m.WorldPosition.ToString(), Unsaved = s.HasUnsavedChanges };
