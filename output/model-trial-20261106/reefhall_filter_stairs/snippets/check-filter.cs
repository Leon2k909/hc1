var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
var found = Everything().Where( g => g.Name.StartsWith( "Filter Stair " ) ).Select( g => g.Id.ToString() ).ToArray();
System.IO.File.WriteAllText( "C:/sbox-projects/hc1/forked-shooter-main/output/model-trial-20261106/reefhall_filter_stairs/snippets/reefhall_memory.json", scene.Serialize().ToJsonString() );
var model = Model.Load( "models/props/reefhall/stairs_v1/filter_stair_a.vmdl" );
var room = Model.Load( "models/maps/reefhall/reefhall_filter.vmdl" );
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, session.HasUnsavedChanges, Aquarium = aquarium?.Id.ToString(), Found = found,
    ModelError = model.IsError, ModelTris = model.MeshInfo?.Meshes.Select( q => q.Triangles ).ToArray(),
    RoomError = room.IsError, RoomTris = room.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
