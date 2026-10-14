var root = Project.Current.GetRootPath();
var stage = System.IO.Path.Combine( root, "output/reefhall/consoles/staging" );
var dest = System.IO.Path.Combine( root, "Assets/models/maps/reefhall" );
var backup = System.IO.Path.Combine( root, "output/reefhall/consoles/before-assets" );
System.IO.Directory.CreateDirectory( backup );
var files = System.IO.Directory.GetFiles( stage ).Where( f => new[] { ".obj", ".mtl", ".vmdl" }.Contains( System.IO.Path.GetExtension( f ) ) ).OrderBy( f => System.IO.Path.GetExtension( f ) == ".vmdl" ? 1 : 0 );
foreach ( var file in files )
{
    cancellationToken.ThrowIfCancellationRequested();
    var name = System.IO.Path.GetFileName( file );
    var target = System.IO.Path.Combine( dest, name );
    var saved = System.IO.Path.Combine( backup, name );
    if ( System.IO.File.Exists( target ) && !System.IO.File.Exists( saved ) ) System.IO.File.Copy( target, saved );
    if ( System.IO.File.ReadAllText( target ) != System.IO.File.ReadAllText( file ) ) System.IO.File.Copy( file, target, true );
}
return new { Model = Editor.AssetSystem.RegisterFile( System.IO.Path.Combine( dest, "reefhall_control.vmdl" ) )?.Path, Backup = backup };
