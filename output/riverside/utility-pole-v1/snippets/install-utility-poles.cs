var session = Editor.SceneEditorSession.Active;
if ( session == null || session.Scene.Name != "riverside" ) throw new Exception( "Riverside is not the active document: " + session?.Scene.Name );
if ( session.HasUnsavedChanges || Game.IsPlaying ) throw new Exception( "Riverside must be a clean, editing document" );
if ( session.Scene.GetAllObjects( false ).Any( g => g.Name == "Utility Poles" ) ) throw new Exception( "Utility Poles is already installed" );
void Check( string path, int[] tris )
{
	var model = Model.Load( path );
	if ( model.IsError || !model.MeshInfo.Meshes.Select( m => m.Triangles ).SequenceEqual( tris ) ) throw new Exception( "Not the built model: " + path );
}
Check( "models/props/riverside/utility_pole_v1/pole_2arm.vmdl", new[] { 1951, 327, 128 } );
Check( "models/props/riverside/utility_pole_v1/pole_1arm.vmdl", new[] { 1567, 291, 92 } );
var project = Sandbox.Project.Current.GetRootPath();
var folder = System.IO.Path.Combine( project, "output/riverside/utility-pole-v1" );
var plan = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( folder, "install-plan.json" ) ) );
string Hash( string p ) => Convert.ToHexString( System.Security.Cryptography.SHA256.HashData( System.IO.File.ReadAllBytes( p ) ) ).ToLowerInvariant();
var relative = plan["source"].GetValue<string>();
if ( relative.Contains( ".." ) || !relative.StartsWith( "Assets/models/maps/riverside/" ) ) throw new Exception( "Unexpected mesh target" );
var target = System.IO.Path.Combine( project, relative );
var staged = System.IO.Path.Combine( project, plan["staged"].GetValue<string>() );
if ( Hash( target ) != plan["source_before"].GetValue<string>() || Hash( staged ) != plan["source_after"].GetValue<string>() ) throw new Exception( "The dressing mesh changed since it was staged" );
var sceneHash = Hash( System.IO.Path.Combine( project, "Assets/scenes/maps/Riverside/riverside.scene" ) );
if ( sceneHash != plan["scene_before"].GetValue<string>() && ( plan["scene_reverted"] == null || sceneHash != plan["scene_reverted"].GetValue<string>() ) ) throw new Exception( "The Riverside scene file changed since it was staged (or since revert.py saved it)" );
var dressing = Model.Load( "models/maps/riverside/riverside_dressing.vmdl" );
if ( dressing.IsError ) throw new Exception( "The dressing model does not load" );
var dressingBefore = dressing.MeshInfo.Meshes.Sum( m => m.Triangles );
var poles = new[] {
	new { Name = "Utility Pole 1", Pos = "-5.0000,110.0000,96.0000", Yaw = "-84.2894", Model = "models/props/riverside/utility_pole_v1/pole_2arm.vmdl" },
	new { Name = "Utility Pole 2", Pos = "520.0000,255.0000,96.0000", Yaw = "-84.2894", Model = "models/props/riverside/utility_pole_v1/pole_2arm.vmdl" },
	new { Name = "Utility Pole 3", Pos = "1050.0000,340.0000,0.0000", Yaw = "-84.2894", Model = "models/props/riverside/utility_pole_v1/pole_2arm.vmdl" },
	new { Name = "Utility Pole 4", Pos = "1720.0000,500.0000,0.0000", Yaw = "-84.2894", Model = "models/props/riverside/utility_pole_v1/pole_2arm.vmdl" },
	new { Name = "Utility Pole 5", Pos = "2330.0000,660.0000,0.0000", Yaw = "-84.2894", Model = "models/props/riverside/utility_pole_v1/pole_2arm.vmdl" },
	new { Name = "Utility Pole 6", Pos = "2880.0000,750.0000,0.0000", Yaw = "-84.2894", Model = "models/props/riverside/utility_pole_v1/pole_2arm.vmdl" },
	new { Name = "Utility Pole 7", Pos = "1060.0000,-230.0000,0.0000", Yaw = "90.0000", Model = "models/props/riverside/utility_pole_v1/pole_1arm.vmdl" },
	new { Name = "Utility Pole 8", Pos = "1300.0000,-30.0000,0.0000", Yaw = "90.0000", Model = "models/props/riverside/utility_pole_v1/pole_1arm.vmdl" },
	new { Name = "Utility Pole 9", Pos = "1820.0000,60.0000,0.0000", Yaw = "90.0000", Model = "models/props/riverside/utility_pole_v1/pole_1arm.vmdl" },
};
var group = Editor.Mcp.SceneTools.CreateGameObject( name: "Utility Poles" );
var ids = new System.Collections.Generic.List<string>();
foreach ( var p in poles )
{
	var item = Editor.Mcp.SceneTools.CreateGameObject( name: p.Name, parent: group.Id.ToString(), position: p.Pos, angles: "0," + p.Yaw + ",0" );
	Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = p.Model, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
	ids.Add( item.Id.ToString() );
}
Editor.Mcp.SceneTools.SaveScene();
System.IO.File.WriteAllText( System.IO.Path.Combine( folder, "native-objects.json" ), System.Text.Json.JsonSerializer.Serialize( new { Group = group.Id, Objects = ids } ) );
System.IO.File.WriteAllBytes( target, System.IO.File.ReadAllBytes( staged ) );
Editor.AssetSystem.RegisterFile( target );
return new { Group = group.Id, Objects = ids.Count, SceneSaved = true, DressingTrianglesBefore = dressingBefore, RemovedOldTriangles = plan["removed_triangles"].GetValue<int>(), MatchesStaged = Hash( target ) == plan["source_after"].GetValue<string>() };
