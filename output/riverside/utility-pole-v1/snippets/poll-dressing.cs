var m = Model.Load( "models/maps/riverside/riverside_dressing.vmdl" );
return new { m.IsError, Tris = m.MeshInfo == null ? -1 : m.MeshInfo.Meshes.Sum( x => x.Triangles ) };
