var rows = new System.Collections.Generic.List<object>();
foreach ( var p in new[] { "models/props/reefhall/lobby_rail_v1/lobby_rail_section.vmdl", "models/props/reefhall/lobby_rail_v1/lobby_rail_section_end.vmdl" } )
{
    var m = Model.Load( p );
    rows.Add( new { p, m.IsError, Mins = m.Bounds.Mins.ToString(), Maxs = m.Bounds.Maxs.ToString(), Tris = m.MeshInfo?.Meshes.Select( q => q.Triangles ).ToArray() } );
}
return rows;