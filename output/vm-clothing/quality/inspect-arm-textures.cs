var paths = new[]
{
    "materials/operators/first_person/fp_army_shirt_color.png",
    "materials/operators/first_person/fp_fingerless_gloves_albedo.png",
    "materials/operators/first_person/fp_fingerless_gloves_color.png",
    "materials/operators/first_person/fp_army_shirt_color.jpg",
    "materials/operators/first_person/fp_fingerless_gloves_albedo.jpg"
};
var textures = paths.Select( path =>
{
    var texture = Texture.Load( path );
    return new { Path = path, Null = texture is null, Valid = texture?.IsValid,
        Error = texture?.IsError, Width = texture?.Width, Height = texture?.Height,
        ResourcePath = texture?.ResourcePath };
}).ToArray();
var materialPaths = new[]
{
    "models/citizen_clothes/shirt/army_shirt/textures/army_shirt.vmat",
    "models/citizen_clothes/gloves/fingerless_gloves/textures/fingerless_gloves.vmat"
};
var materials = materialPaths.Select( path =>
{
    var material = Material.Load( path );
    var color = material?.GetTexture( "g_tColor" );
    var normal = material?.GetTexture( "g_tNormal" );
    return new { Path = path, Null = material is null, Error = material?.IsError,
        Shader = material?.ShaderName, Color = color?.ResourcePath,
        ColorWidth = color?.Width, ColorHeight = color?.Height,
        Normal = normal?.ResourcePath, NormalWidth = normal?.Width, NormalHeight = normal?.Height };
}).ToArray();
var runtime = Game.ActiveScene?.GetAllObjects( true )
    .SelectMany( go => go.Components.GetAll<SkinnedModelRenderer>() )
    .Where( r => r.Model is not null && (r.Model.Name.Contains( "army_shirt" )
        || r.Model.Name.Contains( "fingerless_gloves" ) || r.GameObject.Name == "Clothing" ) )
    .Take( 30 ).Select( r => new { Name = r.GameObject.Name, Model = r.Model.Name,
        Materials = r.Model.Materials.Select( (m, i) => new
        {
            Original = m?.Name,
            Override = r.Materials.GetOverride( i )?.Name,
            Albedo = r.Materials.GetOverride( i )?.GetTexture( "g_tColor" )?.ResourcePath,
            Width = r.Materials.GetOverride( i )?.GetTexture( "g_tColor" )?.Width
        }).ToArray() } ).ToArray();
return new { Textures = textures, BaseMaterials = materials, Runtime = runtime };
