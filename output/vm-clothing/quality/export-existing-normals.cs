var materials = new[]
{
    ("shirt", "models/citizen_clothes/shirt/army_shirt/textures/army_shirt.vmat"),
    ("gloves", "models/citizen_clothes/gloves/fingerless_gloves/textures/fingerless_gloves.vmat")
};
var results = new System.Collections.Generic.List<object>();
foreach ( var (name, path) in materials )
{
    var material = Material.Load( path );
    var normal = material?.GetTexture( "g_tNormal" );
    if ( normal is null || !normal.IsValid || normal.IsError )
        throw new System.Exception( $"Normal missing on {path}" );
    // Preserve the garment's authored large-scale seam and fold normals as the base for new microdetail.
    var bitmap = normal.GetBitmap( 0 );
    var bytes = bitmap.ToPng();
    var output = System.IO.Path.Combine( exchangeDirectory, $"fp_{name}_source_normal.png" );
    await System.IO.File.WriteAllBytesAsync( output, bytes );
    results.Add( new { Name = name, normal.Width, normal.Height, Bytes = bytes.Length, Output = output } );
}
return results;
