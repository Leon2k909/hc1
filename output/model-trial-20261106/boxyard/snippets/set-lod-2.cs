
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
int n = 0;
using ( s.Scene.Push() )
{
    foreach ( var r in s.Scene.GetAllComponents<ModelRenderer>() )
    {
        var path = r.Model?.ResourcePath ?? "";
        if ( !path.Contains( "perimeter_wall_v1" ) ) continue;
        r.LodOverride = 2;
        n++;
    }
}
await Task.Delay( 300 );
return new { n, Active = Editor.SceneEditorSession.Active?.Scene.Name };
