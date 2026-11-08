var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Active = Editor.SceneEditorSession.Active?.Scene.Name, Removed = 0, Left = -1, Saved = false };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var items = Everything().Where( g => g.Name.StartsWith( "Filter Stair " ) ).ToList();
foreach ( var g in items ) Editor.Mcp.SceneTools.DeleteGameObject( g.Id.ToString() );
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 600 );
return new { Retry = false, Active = Editor.SceneEditorSession.Active?.Scene.Name, Removed = items.Count, Left = Everything().Count( g => g.Name.StartsWith( "Filter Stair " ) ), Saved = !session.HasUnsavedChanges };
