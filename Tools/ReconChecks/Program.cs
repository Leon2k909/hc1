using Facepunch;
using Sandbox;
using System.Globalization;
using System.Text.Json;

var root = args.Length > 0 ? Path.GetFullPath( args[0] ) : Path.GetFullPath( Path.Combine( AppContext.BaseDirectory, "../../../../../" ) );
using var prefab = JsonDocument.Parse( File.ReadAllText( Path.Combine( root, "Assets/weapons/recon_nano/recon_nano_airborne.prefab" ) ) );
var drone = prefab.RootElement.GetProperty( "RootObject" ).GetProperty( "Components" ).EnumerateArray()
	.Single( c => c.GetProperty( "__type" ).GetString() == "Facepunch.ReconOctocopter" );
var mins = ParseVector( drone.GetProperty( "Hull" ).GetProperty( "Mins" ).GetString() );
var maxs = ParseVector( drone.GetProperty( "Hull" ).GetProperty( "Maxs" ).GetString() );
var hull = new BBox( mins, maxs );
var widest = drone.GetProperty( "WideFieldOfView" ).GetSingle();
int checks = 0;
Check( Near( ReconFlightMath.FieldOfView( 1, widest ), 62 ), "nano wide FOV" );
Check( Near( ReconFlightMath.FieldOfView( 2, widest ), 33.443721f ), "2x pinhole FOV" );
Check( Near( ReconFlightMath.FieldOfView( 4, widest ), 17.085643f ), "4x pinhole FOV" );
Check( Near( ReconFlightMath.FieldOfView( 1, 48 ), 48 ), "per-aircraft wide FOV" );
Check( Near( ReconFlightMath.FieldOfView( 0, 62 ), 62 ), "invalid zoom clamps to wide" );
Check( Near( ReconFlightMath.FieldOfView( 30, 62 ), 2.29475f ), "octocopter 30x regression" );

// Rotating the asymmetric tail envelope must enclose every corner without making the hull a large fixed cube.
for ( int yaw = -180; yaw <= 180; yaw += 5 )
for ( int pitch = -28; pitch <= 28; pitch += 7 )
for ( int roll = -28; roll <= 28; roll += 7 )
{
	var rotation = Rotation.From( pitch, yaw, roll );
	var box = ReconFlightMath.RotatedHull( hull, rotation );
	for ( int i = 0; i < 8; i++ )
	{
		var corner = rotation * new Vector3( (i & 1) == 0 ? mins.x : maxs.x,
			(i & 2) == 0 ? mins.y : maxs.y, (i & 4) == 0 ? mins.z : maxs.z );
		Check( corner.x >= box.Mins.x - .0001f && corner.x <= box.Maxs.x + .0001f
			&& corner.y >= box.Mins.y - .0001f && corner.y <= box.Maxs.y + .0001f
			&& corner.z >= box.Mins.z - .0001f && corner.z <= box.Maxs.z + .0001f, "rotated tail envelope" );
	}
}
var quarterTurn = ReconFlightMath.RotatedHull( hull, Rotation.FromYaw( 90 ) );
Check( Near( quarterTurn.Maxs.x - quarterTurn.Mins.x, maxs.y - mins.y ), "90 degree width" );
Check( Near( quarterTurn.Maxs.y - quarterTurn.Mins.y, maxs.x - mins.x ), "90 degree tail length" );

foreach ( float pitch in new[] { -80f, -45f, 0f, 45f, 80f } )
for ( int yaw = -180; yaw <= 180; yaw += 15 )
{
	var eye = new Vector3( 137, -281, 137 );
	var aim = Rotation.From( pitch, yaw, 0 );
	var local = aim.Inverse * (ReconFlightMath.HandReleasePoint( eye, aim, 32 ) - eye);
	Check( Near( local.x, 32 ) && Near( local.y, -9 ) && Near( local.z, -10 ), "release follows pitched view" );
}

// The exact hand release helper used by ReconTabletLink, at all stances/headings.
foreach ( float height in new[] { 16f, 32f, 60f } )
for ( int yaw = -180; yaw <= 180; yaw += 15 )
{
	var eye = new Vector3( 137, -281, 77 + height );
	var heading = Rotation.FromYaw( yaw );
	var start = ReconFlightMath.HandReleasePoint( eye, heading, 0 );
	var release = ReconFlightMath.HandReleasePoint( eye, heading, 32 );
	var local = heading.Inverse * (release - eye);
	Check( Near( local.x, 32 ) && Near( local.y, -9 ) && Near( local.z, -10 ), "stance-relative release" );
	Check( Near( (release - start).Length, 32 ), "full volume sweep distance" );
	Check( release.z + hull.Mins.z > 77, "prone release clears floor" );
}
Console.WriteLine( $"PASS: {checks} recon math checks using s&box Vector3, Rotation and BBox." );

bool Near( float a, float b ) => MathF.Abs( a - b ) < .005f;
void Check( bool good, string name ) { checks++; if ( !good ) throw new Exception( $"FAIL: {name}" ); }
Vector3 ParseVector( string text ) { var values = text.Split( ',' ).Select( s => float.Parse( s, CultureInfo.InvariantCulture ) ).ToArray(); return new( values[0], values[1], values[2] ); }
