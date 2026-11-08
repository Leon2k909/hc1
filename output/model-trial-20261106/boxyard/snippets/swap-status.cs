
var sessions = Editor.SceneEditorSession.All.Select( s => s.Scene?.Name + (s == Editor.SceneEditorSession.Active ? "*" : "") ).ToList();
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
int perimeter = 0, yardRenderers = 0, groups = 0, withLod = 0;
using ( s.Scene.Push() )
{
    foreach ( var go in s.Scene.GetAllObjects( true ) ) if ( go.Name == "Perimeter Wall" ) groups++;
    foreach ( var r in s.Scene.GetAllComponents<ModelRenderer>() )
    {
        var path = r.Model?.ResourcePath ?? "";
        if ( path.Contains( "perimeter_wall_v1" ) ) { perimeter++; if ( r.LodOverride != null ) withLod++; }
        if ( path.EndsWith( "boxyard_yard.vmdl" ) ) yardRenderers++;
    }
}
var yard = Model.Load( "models/maps/boxyard/boxyard_yard.vmdl" );
return new { Sessions = sessions, groups, perimeter, withLod, yardRenderers, Yard = new { yard.IsError, Bounds = yard.Bounds.ToString() }, s.HasUnsavedChanges, Playing = Game.IsPlaying };
