using Facepunch;

var checks = 0;
void Check( bool condition, string label )
{
	checks++;
	if ( !condition ) throw new Exception( label );
}
void Near( float a, float b, string label ) => Check( MathF.Abs( a - b ) < 0.001f, $"{label}: {a} != {b}" );
var box = new BBox( new Vector3( -16f, -16f, 0f ), new Vector3( 16f, 16f, 64f ) );

// Check the whole square player hull, including diagonal corners, against pipes and their flanges.
foreach ( var radius in new[] { 3f, 5.5f, 15f, 19.8f, 32f } )
for ( var angle = 0; angle < 360; angle++ )
{
	var outward = Rotation.FromYaw( angle ).Forward;
	var distance = PipeClimbMath.Standoff( outward, box, radius );
	var centre = outward * distance;
	var nearest = new Vector3( MathF.Max( 0f, MathF.Abs( centre.x ) - 16f ), MathF.Max( 0f, MathF.Abs( centre.y ) - 16f ), 0f );
	Check( nearest.Length >= radius + PipeClimbMath.Clearance - 0.001f, "Player corners clear the pipe at every angle" );
	foreach ( var frameRate in new[] { 20f, 60f, 144f } )
	{
		var turned = PipeClimbMath.OutwardAt( outward, 1f, 1f / frameRate );
		Near( turned.Length, 1f, "Orbit keeps its unit radius" );
		var next = turned * PipeClimbMath.Standoff( turned, box, radius );
		var midpoint = (centre + next) * 0.5f;
		var nearestMid = new Vector3( MathF.Max( 0f, MathF.Abs( midpoint.x ) - 16f ), MathF.Max( 0f, MathF.Abs( midpoint.y ) - 16f ), 0f );
		Check( nearestMid.Length > radius, "Orbit chords stay outside the solid pipe" );
	}
	var jump = PipeClimbMath.JumpVelocity( outward );
	Near( jump.z, 180f, "Jump lifts off" );
	Near( jump.WithZ( 0f ).Length, 150f, "Jump leaves the pipe sideways" );
	Check( jump.Dot( outward ) > 149f, "Jump pushes away from the pipe" );
}

foreach ( var frameRate in new[] { 20f, 60f, 144f } )
{
	var height = 90f;
	for ( var frame = 0; frame < (int)frameRate; frame++ ) height = PipeClimbMath.StepHeight( height, 90f, 440f, 1f, 90f, 1f / frameRate );
	Near( height, 180f, "Climb speed is independent of frame rate" );
	for ( var frame = 0; frame < (int)frameRate; frame++ ) height = PipeClimbMath.StepHeight( height, 90f, 440f, -1f, 90f, 1f / frameRate );
	Near( height, 90f, "Descending returns to the starting height" );
	Near( PipeClimbMath.StepHeight( height, 90f, 440f, 0f, 90f, 1f / frameRate ), height, "No input holds the grip without sliding" );
}
Near( PipeClimbMath.StepHeight( 376f, 90f, 440f, 1f, 90f, 0.05f ), 376f, "Hands cannot climb above the pipe end" );
Near( PipeClimbMath.StepHeight( 38f, 90f, 440f, -1f, 90f, 0.05f ), 38f, "Hands cannot climb below the pipe start" );
Near( PipeClimbMath.StepHeight( 100f, 90f, 440f, 1f, 90f, 10f ), 104.5f, "A stalled frame cannot teleport the player" );
Console.WriteLine( $"PASS: {checks} pipe climb geometry and movement checks" );
