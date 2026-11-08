
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var list = s.Scene.GetAllComponents<CameraComponent>().Select( c => new {
    Obj = c.GameObject.Name, Flags = c.GameObject.Flags.ToString(), Pos = c.WorldPosition.ToString(), Ang = c.WorldRotation.Angles().ToString(),
    Fov = c.FieldOfView, Axis = c.FovAxis.ToString(), Main = c.IsMainCamera, En = c.Enabled, Prio = c.Priority, IsSceneCam = c == s.Scene.Camera } ).ToList();
return new { Unsaved = s.HasUnsavedChanges, Active = Editor.SceneEditorSession.Active?.Scene.Name, Cams = list };
