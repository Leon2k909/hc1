
var sessions = Editor.SceneEditorSession.All.Select( s => new {
    Name = s.Scene?.Name, Active = s == Editor.SceneEditorSession.Active, Path = s.Scene?.Source?.ResourcePath,
    Cam = ( s.Scene?.GetAllComponents<CameraComponent>().FirstOrDefault( c => c.GameObject.Name == "editor_camera" ) ?? s.Scene?.Camera ) is CameraComponent c
        ? new { Obj = c.GameObject.Name, Pos = c.WorldPosition.ToString(), Ang = c.WorldRotation.Angles().ToString(), Fov = c.FieldOfView, Axis = c.FovAxis.ToString() } : null } ).ToList();
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, Playing = Game.IsPlaying, Sessions = sessions };
