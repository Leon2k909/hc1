
var view = Editor.SceneViewWidget.Current;
var vp = view?.LastSelectedViewportWidget;
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, FrontView = view?.Session?.Scene?.Name,
    Pos = vp?.State.CameraPosition.ToString(), Ang = vp?.State.CameraRotation.Angles().ToString(), Size = vp?.Size.ToString() };
