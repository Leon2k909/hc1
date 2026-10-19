using Facepunch;

var checks = 0;
void Check( bool condition, string label )
{
	checks++;
	if ( !condition ) throw new Exception( label );
}
void Near( float actual, float expected, string label ) => Check( MathF.Abs( actual - expected ) < .003f, $"{label}: {actual} != {expected}" );
void NearPoint( Vector3 actual, Vector3 expected, string label ) => Check( actual.Distance( expected ) < .003f, $"{label}: {actual} != {expected}" );

// Exercise the production pose through entry and recovery, from standing and crouched gaits.
foreach ( var stance in new[]
{
	(Hips: new Vector3( 0f, 0f, 26f ), Upper: new Vector3( 0f, 4f, 25f ), Lower: new Vector3( 14f, 4f, 20f ), Foot: new Vector3( 6f, 4f, 4f )),
	(Hips: new Vector3( 0f, 0f, 38f ), Upper: new Vector3( 0f, 4f, 37f ), Lower: new Vector3( 2f, 4f, 20f ), Foot: new Vector3( 6f, 4f, 4f )),
	// The installed citizen_human_male skeleton's actual bind-pose joint positions (Source2Viewer DATA).
	(Hips: new Vector3( .197f, 0f, 36.614f ), Upper: new Vector3( -.261f, 3.923f, 34.875f ), Lower: new Vector3( -.6f, 5.761f, 18.932f ), Foot: new Vector3( -1.927f, 7.432f, 3.61f ))
} )
foreach ( var yaw in new[] { 0f, 45f, 90f, 180f, -135f } )
foreach ( var scale in new[] { .8f, 1f, 1.2f } )
foreach ( var tucked in new[] { false, true } )
{
	var root = new Transform( new Vector3( 113f, -241f, 19f ), Rotation.FromYaw( yaw ), scale );
	var hips = root.PointToWorld( stance.Hips );
	var from = new Transform( hips, root.Rotation, root.Scale );
	Vector3 Side( Vector3 point ) => point.WithY( point.y * (tucked ? 1f : -1f) );
	var upper = root.ToWorld( new Transform( Side( stance.Upper ) ) );
	var lower = root.ToWorld( new Transform( Side( stance.Lower ) ) );
	var foot = root.ToWorld( new Transform( Side( stance.Foot ) ) );
	var a = upper.Position.Distance( lower.Position );
	var b = lower.Position.Distance( foot.Position );
	Vector3? lastFoot = null;
	for ( var step = 0; step <= 100; step++ )
	{
		var blend = step / 100f;
		var to = ThirdPersonSlidePose.HipSpace( root, hips, blend );
		Transform Shift( Transform pose ) => to.ToWorld( from.ToLocal( pose ) );
		ThirdPersonSlidePose.SolveSlideLeg( Shift( upper ), Shift( lower ), Shift( foot ), foot, root, blend, tucked,
			out var thigh, out var calf, out var boot );
		Near( thigh.Position.Distance( calf.Position ), a, "Thigh length stays fixed" );
		Near( calf.Position.Distance( boot.Position ), b, "Shin length stays fixed" );
		Check( root.PointToLocal( boot.Position ).z >= MathF.Min( stance.Foot.z, 4f ) - .1f, "Boot stays above the floor throughout the transition" );
		Check( root.PointToLocal( calf.Position ).z >= 0f, "Knee stays above the floor" );
		if ( lastFoot.HasValue ) Check( lastFoot.Value.Distance( boot.Position ) < 1f * scale, "No discontinuity between blend steps" );
		lastFoot = boot.Position;
		if ( step == 0 )
		{
			NearPoint( thigh.Position, upper.Position, "Original hip restored at zero blend" );
			NearPoint( calf.Position, lower.Position, "Original knee restored at zero blend" );
			NearPoint( boot.Position, foot.Position, "Original ankle restored at zero blend" );
		}
		if ( step == 100 )
		{
				NearPoint( root.PointToLocal( to.Position ), new Vector3( -3f, -4f, 10f ), "Hips finish on the ground" );
			Check( root.PointToLocal( boot.Position ).x > (tucked ? 8f : 23f), "Leg has a distinct tucked or extended pose" );
		}
	}
}

// Unreachable targets and a pole parallel to the leg must still produce a finite, unstretched chain.
foreach ( var target in new[] { new Vector3( 500f, 0f, 0f ), new Vector3( .01f, 0f, 0f ), new Vector3( 0f, 0f, 500f ) } )
{
	var upper = new Transform( Vector3.Zero );
	var lower = new Transform( new Vector3( 0f, 0f, -16f ) );
	var foot = new Transform( new Vector3( 0f, 0f, -34f ) );
	ThirdPersonSlidePose.SolveLeg( upper, lower, foot, target, target, Rotation.Identity, out var thigh, out var calf, out var boot );
	Near( thigh.Position.Distance( calf.Position ), 16f, "Out-of-range target preserves thigh" );
	Near( calf.Position.Distance( boot.Position ), 18f, "Out-of-range target preserves shin" );
}

Console.WriteLine( $"PASS: {checks} third-person slide geometry checks" );
