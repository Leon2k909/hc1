var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Active = Editor.SceneEditorSession.Active?.Scene.Name, Objects = new string[0], Saved = false };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
if ( Everything().Any( g => g.Name.StartsWith( "Rotunda Stair " ) ) ) throw new Exception( "These stairs are already in the scene" );
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
if ( aquarium == null ) throw new Exception( "No Aquarium object in the scene" );
var plan = new[] { new { Name = "Rotunda Stair NE", Position = "0,-0,0", Model = "models/props/reefhall/stairs_v1/rotunda_stair_ne.vmdl" }, new { Name = "Rotunda Stair NW", Position = "0,-0,0", Model = "models/props/reefhall/stairs_v1/rotunda_stair_nw.vmdl" } };
var ids = new System.Collections.Generic.List<string>();
foreach ( var p in plan )
{
    var model = Model.Load( p.Model );
    if ( model.IsError ) throw new Exception( "The stair model did not load: " + p.Model );
    var item = Editor.Mcp.SceneTools.CreateGameObject( name: p.Name, parent: aquarium.Id.ToString(), position: p.Position, angles: "0,0,0" );
    Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = model.ResourcePath, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
    ids.Add( item.Id.ToString() );
}
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 600 );
return new { Retry = false, Active = Editor.SceneEditorSession.Active?.Scene.Name, Objects = ids.ToArray(), Saved = !session.HasUnsavedChanges };
