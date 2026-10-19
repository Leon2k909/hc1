var scene = Editor.SceneEditorSession.Active?.Scene;
if ( scene is null ) return "No editable scene";
if ( scene.Name.ToLowerInvariant() != "lowtide" ) return $"Wrong scene: {scene.Name}";
var world = scene.GetAllObjects( true ).FirstOrDefault( o => o.Name == "Lowtide" );
if ( world is null ) return "Lowtide root missing";
var existing = scene.GetAllObjects( true ).FirstOrDefault( o => o.Name == "Downpipe Collisions" );
if ( existing is not null ) return "Downpipe Collisions already exists; no duplicate created";
var path = @"C:\sbox-projects\hc1\forked-shooter-main\output\lowtide\downpipe-colliders.csv";
var lines = System.IO.File.ReadAllLines( path );
if ( lines.Length != 56 ) return $"Expected 56 pipe collision segments, found {lines.Length}";
var group = new GameObject( world, true, "Downpipe Collisions" );
int count = 0;
foreach ( var line in lines )
{
    var row = line.Split( ',' );
    float Parse( string number ) => float.Parse( number, System.Globalization.CultureInfo.InvariantCulture );
    var go = new GameObject( group, true, row[0] );
    go.WorldPosition = new Vector3( Parse(row[1]), Parse(row[2]), Parse(row[3]) );
    var capsule = go.Components.Create<CapsuleCollider>();
    capsule.Start = new Vector3( 0, 0, Parse(row[5]) );
    capsule.End = new Vector3( 0, 0, Parse(row[4]) - Parse(row[5]) );
    capsule.Radius = Parse(row[5]);
    capsule.Static = true;
    capsule.IsTrigger = false;
    count++;
}
return $"Added {count} static pipe collision segments to {scene.Name}";
