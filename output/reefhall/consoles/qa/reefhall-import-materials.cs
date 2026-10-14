var root = Project.Current.GetRootPath();
var dest = System.IO.Path.Combine( root, "Assets/materials/reefhall/consoles" );
System.IO.Directory.CreateDirectory( dest );
var imagePath = System.IO.Path.Combine( dest, "rh_console_screen_atlas.png" );
System.IO.File.Copy( @"C:\Users\leon2\.codex\generated_images\01a13a7f-8d69-7303-a893-790728b2908e\exec-58770afe-b109-48a9-a834-416ae312efb9.png", imagePath, true );
var stage = System.IO.Path.Combine( root, "output/reefhall/consoles/staging/materials" );
var imported = new System.Collections.Generic.List<string>();
foreach ( var file in System.IO.Directory.GetFiles( stage, "*.vmat" ) )
{
    cancellationToken.ThrowIfCancellationRequested();
    var target = System.IO.Path.Combine( dest, System.IO.Path.GetFileName( file ) );
    System.IO.File.Copy( file, target, true );
    var asset = Editor.AssetSystem.RegisterFile( target );
    if ( asset is null ) throw new Exception( "Could not register " + target );
    imported.Add( target );
}
return imported;
