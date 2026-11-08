var apply = true;
var project = Sandbox.Project.Current.GetRootPath();
var folder = System.IO.Path.Combine( project, "output/riverside/utility-pole-v1" );
var ids = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( folder, "native-objects.json" ) ) );
var groupId = Guid.Parse( ids["Group"].GetValue<string>() );
var itemIds = ids["Objects"].AsArray().Select( n => Guid.Parse( n.GetValue<string>() ) ).ToList();
var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "riverside" );
if ( session == null ) throw new Exception( "Riverside is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) );
var group = Everything().FirstOrDefault( g => g.Id == groupId );
string state = "absent";
if ( group != null )
{
	bool ok = group.Name == "Utility Poles" && group.Children.Count == itemIds.Count && group.Components.GetAll().Count() == 0;
	foreach ( var item in group.Children )
	{
		var renderer = item.Components.Get<ModelRenderer>();
		ok &= itemIds.Contains( item.Id ) && item.Name.StartsWith( "Utility Pole " ) && renderer != null && renderer.Model != null
			&& renderer.Model.ResourcePath.StartsWith( "models/props/riverside/utility_pole_v1/pole_" ) && item.Components.GetAll().Count() == 1;
	}
	if ( !ok ) throw new Exception( "The Utility Poles objects are not what install.py made; look at them in the editor first" );
	state = "installed";
}
System.IO.File.WriteAllText( "C:/sbox-projects/hc1/forked-shooter-main/output/riverside/utility-pole-v1/snippets/riverside_memory.json", scene.Serialize().ToJsonString() );
if ( apply && state == "installed" )
{
	if ( Editor.SceneEditorSession.Active != session ) throw new Exception( "Riverside is not the front document" );
	Editor.Mcp.SceneTools.DeleteGameObject( groupId.ToString() );
	Editor.Mcp.SceneTools.SaveScene();
	await Task.Delay( 300 );
	return new { State = "deleted", Gone = !Everything().Any( g => g.Id == groupId ), session.HasUnsavedChanges };
}
return new { State = state, session.HasUnsavedChanges, Front = Editor.SceneEditorSession.Active == session };
