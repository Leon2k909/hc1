using Facepunch;

var checks = 0;
void Check( bool condition, string label )
{
	checks++;
	if ( !condition ) throw new Exception( label );
}
void Near( float a, float b, string label ) => Check( MathF.Abs( a - b ) < 0.002f, $"{label}: {a} != {b}" );
void NearPoint( Vector3 a, Vector3 b, string label ) => Check( a.Distance( b ) < 0.002f, $"{label}: {a} != {b}" );

// A standing rifleman's joints, in model space. Check the actual production pose math, without a running engine.
Vector3[] joints =
{
	new( 0f, 0f, 38f ), // pelvis
	new( 1f, 0f, 48f ), // spine
	new( 2f, 0f, 57f ), // neck
	new( 2f, 0f, 64f ), // head
	new( 6f, 0f, 64f ), // eyes
	new( 1f, -5f, 37f ), // hip
	new( 2f, -5f, 20f ), // knee
	new( 6f, -5f, 3f ), // ankle
	new( 1f, 5f, 37f ),
	new( 2f, 5f, 20f ),
	new( 6f, 5f, 3f )
};
var parents = new[] { -1, 0, 1, 2, 3, 0, 5, 6, 0, 8, 9 };

foreach ( var yaw in new[] { 0f, 45f, 90f, 180f, -135f } )
foreach ( var scale in new[] { 0.8f, 1f, 1.2f } )
{
	var root = new Transform( new Vector3( 113f, -241f, 19f ), Rotation.FromYaw( yaw ), scale );
	var hips = root.PointToWorld( joints[0] );
	var from = new Transform( hips, root.Rotation, root.Scale );
	for ( var step = 0; step <= 20; step++ )
	{
		var blend = step / 20f;
		var to = BotPronePose.PoseSpace( root, hips, blend );
		var neck = to.PointToWorld( from.PointToLocal( root.PointToWorld( joints[2] ) ) );
		var headLift = root.Rotation * Rotation.FromPitch( -80f * blend ) * root.Rotation.Inverse;
		var posed = joints.Select( (point, i) => BotPronePose.PoseBone(
			root.ToWorld( new Transform( point ) ), from, to, neck, headLift, i is 2 or 3 or 4 ) ).ToArray();
		for ( var i = 1; i < joints.Length; i++ )
			Near( posed[i].Position.Distance( posed[parents[i]].Position ), joints[i].Distance( joints[parents[i]] ) * scale,
				$"Bone length, yaw {yaw}, scale {scale}, blend {blend}, joint {i}" );
		NearPoint( posed[3].Rotation.Forward, root.Rotation.Forward, "Head stays facing forward rather than into the floor" );
		Check( root.PointToLocal( posed[7].Position ).z >= -0.1f, "Right foot stays above the floor during the transition" );
		Check( root.PointToLocal( posed[10].Position ).z >= -0.1f, "Left foot stays above the floor during the transition" );
		if ( step == 0 )
			for ( var i = 0; i < joints.Length; i++ ) NearPoint( posed[i].Position, root.PointToWorld( joints[i] ), "Standing pose unchanged" );
		if ( step == 20 )
		{
			NearPoint( root.PointToLocal( to.Position ), new Vector3( -8f, 0f, 12f ), "Prone hips land at the intended height" );
			Near( Vector3.Dot( to.Rotation.Up, root.Rotation.Forward ), MathF.Sin( 80f.DegreeToRadian() ), "Torso lies forwards" );
		}
	}
}

foreach ( var crouching in new[] { false, true } )
{
	var previous = float.MaxValue;
	for ( var step = 0; step <= 100; step++ )
	{
		var blend = step / 100f;
		var eyes = BotPronePose.EyeOffset( crouching, blend );
		var box = BotPronePose.MovementBounds( crouching, blend );
		Near( box.Mins.z, 0f, "Movement box always starts at the feet" );
		Near( box.Maxs.z, eyes.z, "Eyes and collision height move together" );
		Check( eyes.z <= previous + 0.001f, "Eye height lowers monotonically" );
		Check( box.Size.x >= 32f && box.Size.z >= 24f, "Movement box never collapses" );
		Check( eyes.x >= box.Mins.x && eyes.x <= box.Maxs.x, "Eyes remain over the body footprint" );
		previous = eyes.z;
	}
	NearPoint( BotPronePose.EyeOffset( crouching, -1f ), BotPronePose.EyeOffset( crouching, 0f ), "Negative blend clamps" );
	NearPoint( BotPronePose.EyeOffset( crouching, 2f ), BotPronePose.ProneEye, "Oversized blend clamps" );
}

Console.WriteLine( $"PASS: {checks} bot stance geometry checks" );
