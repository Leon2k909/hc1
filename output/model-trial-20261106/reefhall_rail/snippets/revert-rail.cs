var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Found = 0, Left = -1, Saved = false };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var ids = new System.Collections.Generic.HashSet<string> { "56c95911-974e-4be6-8b92-d88696c16138", "eaf0d4b4-c9b9-4752-af46-8d6d4c21d383", "dd9692f2-e688-4caf-88fd-74f7901889e1", "4c2b6e0c-a867-4fdd-9bf7-999cfe93a1cd", "270d164c-9d1c-4ba0-8689-304ffe14cf16", "a7f3b6e8-bf0e-4f57-9562-2c1a135e524d", "db30f507-4b69-46c5-afc5-313f80623b3b", "2853e9fb-6b1c-46ee-8f27-e2e10b3e82f8", "2073108c-f20e-4ce7-a537-297d39222de1", "291d50fd-5c46-435c-9038-6b281f9d579f", "bca92de3-e9d6-40ad-95d8-d028af769ffd", "af898a7f-9bfa-4f5e-9af9-db2699e5a8b9", "032bfe10-519f-4914-bb99-d1a714c7129e", "6772afbf-79df-40a3-859b-10ec330cf9e5" };
var rails = Everything().Where( g => g.Name.StartsWith( "Lobby Rail " ) ).ToArray();
if ( rails.Length != 14 ) throw new Exception( "Expected 14 lobby rail objects, found " + rails.Length + "; nothing deleted" );
if ( ids.Count > 0 && rails.Any( g => !ids.Contains( g.Id.ToString() ) ) ) throw new Exception( "A lobby rail object is not one the install made; nothing deleted" );
foreach ( var g in rails ) Editor.Mcp.SceneTools.DeleteGameObject( g.Id.ToString() );
await Task.Delay( 500 );
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 600 );
var left = Everything().Count( g => g.Name.StartsWith( "Lobby Rail " ) );
return new { Retry = false, Found = rails.Length, Left = left, Saved = !session.HasUnsavedChanges };
