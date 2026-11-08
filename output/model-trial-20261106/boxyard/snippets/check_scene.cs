var sessions = Editor.SceneEditorSession.All.Select( s => s.Scene?.Name + (s == Editor.SceneEditorSession.Active ? "*" : "") ).ToList();
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var found = new System.Collections.Generic.List<object>();
int perimeter = 0, yardRenderers = 0;
var stems = new System.Collections.Generic.Dictionary<string, int>();
using ( s.Scene.Push() )
{
    foreach ( var r in s.Scene.GetAllComponents<ModelRenderer>() )
    {
        var path = r.Model?.ResourcePath ?? "";
        if ( path.Contains( "perimeter_wall_v1" ) )
        {
            perimeter++;
            var stem = System.IO.Path.GetFileNameWithoutExtension( path );
            stems[stem] = ( stems.ContainsKey( stem ) ? stems[stem] : 0 ) + 1;
            if ( perimeter <= 3 ) found.Add( new { r.GameObject.Name, Parent = r.GameObject.Parent?.Name, Pos = r.GameObject.WorldPosition.ToString(), Yaw = r.GameObject.WorldRotation.Yaw(), Err = r.Model.IsError } );
        }
        if ( path.EndsWith( "boxyard_yard.vmdl" ) ) yardRenderers++;
    }
}
var yard = Model.Load( "models/maps/boxyard/boxyard_yard.vmdl" );
return new { Sessions = sessions, perimeter, stems, yardRenderers, found, Yard = new { yard.IsError, Bounds = yard.Bounds.ToString() }, s.HasUnsavedChanges, Playing = Game.IsPlaying };
