var s = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "boxyard" );
bool had = s != null;
bool unsaved = s != null && s.HasUnsavedChanges;
bool closed = false;
if ( s != null && !unsaved ) { s.Destroy(); closed = true; }
await Task.Delay( 1500 );
var v = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "veridant" );
if ( v != null ) { v.BringToFront(); await Task.Delay( 900 ); }
return new { had, unsaved, closed, Playing = Game.IsPlaying,
    Sessions = Editor.SceneEditorSession.All.Select( x => x.Scene?.Name + ( x == Editor.SceneEditorSession.Active ? "*" : "" ) ).ToList() };
