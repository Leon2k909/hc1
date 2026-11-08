
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var before = s.HasUnsavedChanges;
s.Reload();
await Task.Delay( 3500 );
var s2 = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
return new { before, same = object.ReferenceEquals( s, s2 ), s2.HasUnsavedChanges, Active = Editor.SceneEditorSession.Active?.Scene.Name };
