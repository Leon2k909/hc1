var apply = false;
var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var desks = Everything().Where( g => g.Name == "Lobby Reception Desk" ).ToArray();
if ( desks.Length > 1 ) throw new Exception( "More than one reception desk object" );
string state = "absent";
if ( desks.Length == 1 )
{
    var item = desks[0];
    var renderer = item.Components.Get<ModelRenderer>();
    bool ok = item.Parent != null && item.Parent.Name == "Aquarium" && renderer != null && renderer.Model != null
        && renderer.Model.ResourcePath == "models/props/reefhall/reception_desk_v1/reception_desk.vmdl" && item.Components.GetAll().Count() == 1 && item.Children.Count == 0;
    if ( !ok ) throw new Exception( "The reception desk object is not what install.py made; look at it in the editor first" );
    state = "installed";
}
System.IO.File.WriteAllText( "C:/sbox-projects/hc1/forked-shooter-main/output/model-trial-20261106/reefhall/snippets/reefhall_memory.json", scene.Serialize().ToJsonString() );
if ( apply && state == "installed" )
{
    if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
    if ( Editor.SceneEditorSession.Active != session ) return new { State = "retry", HasUnsavedChanges = false, Gone = false };
    Editor.Mcp.SceneTools.DeleteGameObject( desks[0].Id.ToString() );
    Editor.Mcp.SceneTools.SaveScene();
    await Task.Delay( 400 );
    return new { State = "deleted", Gone = !Everything().Any( g => g.Name == "Lobby Reception Desk" ), session.HasUnsavedChanges };
}
return new { State = state, session.HasUnsavedChanges, Gone = false };
