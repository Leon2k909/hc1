var paths = new []
{
    "materials/operators/first_person/fp_army_shirt_color.png",
    "materials/operators/first_person/fp_army_shirt_normal.png",
    "materials/operators/first_person/fp_fingerless_gloves_albedo.png",
    "materials/operators/first_person/fp_fingerless_gloves_normal.png"
};
return paths.Select( path =>
{
    var tex = Texture.Load( path );
    return new { path, Width = tex?.Width, Height = tex?.Height, Valid = tex?.IsValid, Error = tex?.IsError };
}).ToArray();
