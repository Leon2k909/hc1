return Editor.SceneEditorSession.All.Select( s => new {
    Scene = s.Scene?.Name,
    Objects = s.Scene?.GetAllObjects( true ).Where( g => g.Components.Get<ModelRenderer>()?.Model?.ResourcePath?.Contains( "reefhall_control" ) == true ).Select( g => new { g.Name, g.Id, Model = g.Components.Get<ModelRenderer>().Model.ResourcePath, Position = g.WorldPosition.ToString() } ).ToArray()
} ).ToArray();
