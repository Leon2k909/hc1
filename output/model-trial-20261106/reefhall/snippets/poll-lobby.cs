var lobby = Model.Load( "models/maps/reefhall/reefhall_lobby.vmdl" );
return new { lobby.IsError, Tris = lobby.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
