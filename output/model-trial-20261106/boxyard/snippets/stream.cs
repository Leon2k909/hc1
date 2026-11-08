
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var seen = new System.Collections.Generic.HashSet<string>();
var report = new System.Collections.Generic.List<object>();
using ( s.Scene.Push() )
{
    foreach ( var r in s.Scene.GetAllComponents<ModelRenderer>() )
    {
        var path = r.Model?.ResourcePath ?? "";
        if ( !path.Contains( "models/maps/boxyard/" ) && !path.Contains( "models/props/boxyard/" ) ) continue;
        for ( int slot = 0; slot < r.Materials.Count; slot++ )
        {
            var m = r.Materials.GetOverride( slot ) ?? r.Materials.GetOriginal( slot );
            if ( m == null || m.IsError || !seen.Add( m.ResourcePath ?? m.Name ) ) continue;
            int size = ( m.Name ?? m.ResourcePath ?? "" ).Contains( "wall" ) || ( m.ResourcePath ?? "" ).Contains( "bx_concrete" ) || ( m.ResourcePath ?? "" ).Contains( "steel" ) || ( m.ResourcePath ?? "" ).Contains( "galv" ) ? 2048 : 1024;
            var sizes = new System.Collections.Generic.List<string>();
            foreach ( var key in new[] { "g_tColor", "g_tNormal", "g_tRma" } )
            {
                var t = m.GetTexture( key );
                if ( t == null ) continue;
                t.MarkUsed( size );
                sizes.Add( key + ":" + t.Width + "x" + t.Height );
            }
            report.Add( new { Material = m.ResourcePath ?? m.Name, Requested = size, Textures = sizes } );
        }
    }
}
await Task.Delay( 2500 );
return new { Count = report.Count, Active = Editor.SceneEditorSession.Active?.Scene.Name, report };
