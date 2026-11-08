
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var before = Editor.SceneEditorSession.Active?.Scene.Name;
s.BringToFront();
await Task.Delay( 900 );
return new { before, after = Editor.SceneEditorSession.Active?.Scene.Name };
