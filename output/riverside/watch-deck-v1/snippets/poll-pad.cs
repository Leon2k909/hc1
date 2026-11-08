var pad = Model.Load( "models/maps/riverside/riverside_pad.vmdl" );
return new { pad.IsError, Tris = pad.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
