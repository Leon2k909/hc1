var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Active = Editor.SceneEditorSession.Active?.Scene.Name, Object = "" };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
if ( Everything().Any( g => g.Name == "Lobby Reception Desk" ) ) throw new Exception( "The reception desk is already in the scene" );
var model = Model.Load( "models/props/reefhall/reception_desk_v1/reception_desk.vmdl" );
if ( model.IsError ) throw new Exception( "The reception desk model did not load" );
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
if ( aquarium == null ) throw new Exception( "No Aquarium object in the scene" );
var item = Editor.Mcp.SceneTools.CreateGameObject( name: "Lobby Reception Desk", parent: aquarium.Id.ToString(), position: "0,2420,0", angles: "0,0,0" );
Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = model.ResourcePath, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 400 );
return new { Retry = false, Active = Editor.SceneEditorSession.Active?.Scene.Name, Object = item.Id.ToString(), Saved = !session.HasUnsavedChanges };
