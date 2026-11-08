var room = Model.Load( "models/maps/reefhall/reefhall_rotunda.vmdl" );
return new { room.IsError, Tris = room.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
