var room = Model.Load( "models/maps/reefhall/reefhall_filter.vmdl" );
return new { room.IsError, Tris = room.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
