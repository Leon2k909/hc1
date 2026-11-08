var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "cerroblanco" );
var before = Editor.SceneEditorSession.Active?.Scene.Name;
s.BringToFront();
await Task.Delay( 800 );
return new { before, after = Editor.SceneEditorSession.Active?.Scene.Name };
