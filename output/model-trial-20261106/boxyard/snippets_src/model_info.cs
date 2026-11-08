var names = new[] { "perimeter_panel_a_v1", "perimeter_panel_b_v1", "perimeter_panel_c_v1", "perimeter_panel_d_v1", "perimeter_pier_a_v1", "perimeter_pier_b_v1" };
var list = new System.Collections.Generic.List<object>();
foreach ( var n in names )
{
    var m = Model.Load( "models/props/boxyard/perimeter_wall_v1/" + n + ".vmdl" );
    list.Add( new
    {
        Name = n,
        m.IsError,
        Bounds = m.Bounds.ToString(),
        Render = m.RenderBounds.ToString(),
        Mats = string.Join( ",", m.Materials.Select( x => x.Name ) ),
    } );
}
return list;
