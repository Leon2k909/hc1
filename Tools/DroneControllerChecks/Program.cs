using Facepunch;
using System.Text.Json;

var checks = 0;
void Check( bool condition, string label ) { checks++; if ( !condition ) throw new Exception( label ); }
void Near( float actual, float expected, string label ) => Check( MathF.Abs( actual - expected ) < .003f, $"{label}: {actual} != {expected}" );
void NearPoint( Vector3 actual, Vector3 expected, string label ) => Check( actual.Distance( expected ) < .003f, $"{label}: {actual} != {expected}" );

// Both wrists must reach their grips while yaw, stance and character scale change, without stretching the arms.
foreach ( var height in new[] { 56f, 40f, 24f } )
foreach ( var yaw in new[] { -135f, 0f, 45f, 90f, 180f } )
foreach ( var scale in new[] { .8f, 1f, 1.2f } )
foreach ( var sign in new[] { -1, 1 } )
{
	var root = new Transform( new Vector3( 113f, -241f, 19f ), Rotation.FromYaw( yaw ), scale );
	var shoulders = root.PointToWorld( new Vector3( 0, 0, height ) );
	var frame = ThirdPersonTabletPose.StationTransform( root, shoulders );
	var upper = root.ToWorld( new Transform( new Vector3( 0, sign * 7f, height ) ) );
	var lower = root.ToWorld( new Transform( new Vector3( 2, sign * 8f, height - 13f ) ) );
	var hand = root.ToWorld( new Transform( new Vector3( 12, sign * 8f, height - 20f ) ) );
	var wrist = frame.PointToWorld( new Vector3( -.2f, sign * 8.6f, -1.6f ) );
	ThirdPersonTabletPose.SolveArm( upper, lower, hand, wrist, root.Rotation * new Vector3( 0, sign * 12, -20 ),
		frame.Rotation, out var solvedUpper, out var solvedLower, out var solvedHand );
	Near( solvedUpper.Position.Distance( solvedLower.Position ), upper.Position.Distance( lower.Position ), "Upper arm length" );
	Near( solvedLower.Position.Distance( solvedHand.Position ), lower.Position.Distance( hand.Position ), "Forearm length" );
	NearPoint( solvedHand.Position, wrist, "Wrist reaches controller grip" );
	NearPoint( frame.Rotation * Vector3.Forward, root.Rotation * Rotation.FromPitch( 32 ) * Vector3.Forward, "Controller faces the operator at every heading" );
	NearPoint( root.PointToLocal( frame.Position ), new Vector3( 12, 0, height - 8 ), "Controller follows stance and scale" );
}

// Extreme targets and a pole parallel to the arm must remain finite and preserve both bone lengths.
foreach ( var target in new[] { new Vector3( 500, 0, 0 ), new Vector3( .01f, 0, 0 ), new Vector3( 0, 0, 500 ) } )
{
	var upper = new Transform( Vector3.Zero );
	var lower = new Transform( new Vector3( 0, 0, -13 ) );
	var hand = new Transform( new Vector3( 0, 0, -25 ) );
	ThirdPersonTabletPose.SolveArm( upper, lower, hand, target, target, Rotation.Identity,
		out var solvedUpper, out var solvedLower, out var solvedHand );
	Near( solvedUpper.Position.Distance( solvedLower.Position ), 13, "Out-of-range target preserves upper arm" );
	Near( solvedLower.Position.Distance( solvedHand.Position ), 12, "Out-of-range target preserves forearm" );
}

var rootPath = args.Length > 0 ? Path.GetFullPath( args[0] ) : Path.GetFullPath( Path.Combine( AppContext.BaseDirectory, "../../../../../" ) );
foreach ( var aircraft in new[] { "nano", "octocopter" } )
{
	using var prefab = JsonDocument.Parse( File.ReadAllText( Path.Combine( rootPath, $"Assets/Weapons/recon_{aircraft}/wm_recon_{aircraft}.prefab" ) ) );
	var components = prefab.RootElement.GetProperty( "RootObject" ).GetProperty( "Components" ).EnumerateArray().ToArray();
	var wm = components.Single( c => c.GetProperty( "__type" ).GetString() == "Facepunch.WorldModel" );
	Check( wm.GetProperty( "UseTabletPose" ).GetBoolean(), $"{aircraft} uses the dedicated controller pose" );
	var renderer = components.Single( c => c.GetProperty( "__type" ).GetString() == "Sandbox.SkinnedModelRenderer" );
	Check( renderer.GetProperty( "RenderOptions" ).GetProperty( "GameLayer" ).GetBoolean(), $"{aircraft} controller renders in the world" );
}

Console.WriteLine( $"PASS: {checks} drone controller geometry and prefab checks" );
