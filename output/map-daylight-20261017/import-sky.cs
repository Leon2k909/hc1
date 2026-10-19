if ( Game.IsPlaying ) throw new Exception( "Import requires the idle editor." );
var root = Project.Current.GetRootPath();
var stage = System.IO.Path.Combine( root, "output/map-daylight-20261017/sky-stage" );
var destination = System.IO.Path.Combine( root, "Assets/materials/boxyard/sky" );
System.IO.Directory.CreateDirectory( destination );
var imported = new System.Collections.Generic.List<object>();
foreach ( var name in new[] { "boxyard_midday.exr", "boxyard_midday.vmat" } )
{
    cancellationToken.ThrowIfCancellationRequested();
    var source = System.IO.Path.Combine( stage, name );
    var target = System.IO.Path.Combine( destination, name );
    var data = System.IO.File.ReadAllBytes( source );
    if ( System.IO.File.Exists( target ) && !System.IO.File.ReadAllBytes( target ).SequenceEqual( data ) )
        throw new Exception( "Refusing to overwrite a different existing sky asset: " + name );
    if ( !System.IO.File.Exists( target ) )
    {
        var pending = target + ".daylight-import";
        System.IO.File.WriteAllBytes( pending, data );
        System.IO.File.Move( pending, target );
    }
    var asset = Editor.AssetSystem.RegisterFile( target );
    imported.Add( new { name, bytes = data.Length, Registered = asset is not null } );
}
return new { imported };

