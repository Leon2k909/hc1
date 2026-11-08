var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
var rails = Everything().Where( g => g.Name.StartsWith( "Lobby Rail " ) ).Select( g => g.Id.ToString() ).ToArray();
System.IO.File.WriteAllText( "C:/sbox-projects/hc1/forked-shooter-main/output/model-trial-20261106/reefhall_rail/snippets/reefhall_memory.json", scene.Serialize().ToJsonString() );
var models = new[] { "models/props/reefhall/lobby_rail_v1/lobby_rail_section.vmdl", "models/props/reefhall/lobby_rail_v1/lobby_rail_section_end.vmdl" }.Select( Model.Load ).ToArray();
var lobby = Model.Load( "models/maps/reefhall/reefhall_lobby.vmdl" );
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, session.HasUnsavedChanges, Aquarium = aquarium?.Id.ToString(), Rails = rails,
    ModelError = models.Any( m => m.IsError ), ModelTris = models.Select( m => m.MeshInfo?.Meshes.Select( q => q.Triangles ).ToArray() ).ToArray(),
    LobbyError = lobby.IsError, LobbyTris = lobby.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
