
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var wasActive = Editor.SceneEditorSession.Active?.Scene.Name;
if ( Editor.SceneEditorSession.Active != s ) { s.BringToFront(); await Task.Delay( 900 ); }
var view = Editor.SceneViewWidget.Current;
if ( view == null || view.Session != s ) return new { error = "front view is not " + "boxyard", FrontView = view?.Session?.Scene?.Name, WasActive = wasActive };
var vp = view.LastSelectedViewportWidget;
var before = new { Pos = vp.State.CameraPosition.ToString(), Ang = vp.State.CameraRotation.Angles().ToString() };
vp.State.CameraPosition = new Vector3( 690.0f, -430.0f, 64.0f );
vp.State.CameraRotation = Rotation.From( 6.0f, 32.0f, 0f );

await Task.Delay( 900 );
var cam = s.Scene.GetAllComponents<CameraComponent>().First( c => c.GameObject.Name == "editor_camera" );
return new { Scene = s.Scene.Name, WasActive = wasActive, Active = Editor.SceneEditorSession.Active?.Scene.Name, Before = before,
    State = new { Pos = vp.State.CameraPosition.ToString(), Ang = vp.State.CameraRotation.Angles().ToString(), Size = vp.Size.ToString() },
    EditorCam = new { Pos = cam.WorldPosition.ToString(), Ang = cam.WorldRotation.Angles().ToString(), Fov = cam.FieldOfView } };
