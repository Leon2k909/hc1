using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
foreach ( var radius in new[] { 1f, 128f, 512f, 2048f } )
{
	var previous = BlastImpulseRules.Magnitude( 0f, radius );
	Check( previous == radius * 50f, "Near-source force must retain the existing authored envelope." );
	for ( var step = 1; step <= 16; step++ )
	{
		var force = BlastImpulseRules.Magnitude( radius * step / 16f, radius );
		Check( force >= 0f && force < previous, "Increasing distance must strictly reduce force throughout the damage radius." );
		previous = force;
	}
	Check( previous == 0f && BlastImpulseRules.Magnitude( radius * 2f, radius ) == 0f,
		"Targets on or beyond the blast radius must receive no impulse." );
	Check( BlastImpulseRules.Magnitude( radius / 2f, radius ) == radius / 2f * 50f,
		"Mid-radius force must retain its previous magnitude." );
}
foreach ( var invalid in new[] { float.NaN, float.PositiveInfinity, float.NegativeInfinity } )
{
	Check( BlastImpulseRules.Magnitude( invalid, 512f ) == 0f, "Invalid distance must not produce force." );
	Check( BlastImpulseRules.Magnitude( 10f, invalid ) == 0f, "Invalid radius must not produce force." );
}
Check( BlastImpulseRules.Magnitude( 10f, 0f ) == 0f && BlastImpulseRules.Magnitude( 10f, -512f ) == 0f,
	"Zero/negative radius must disable force." );
Check( BlastImpulseRules.Magnitude( -10f, 512f ) == BlastImpulseRules.Magnitude( 0f, 512f ),
	"Negative distance must be clamped at the source." );
Check( float.IsFinite( BlastImpulseRules.Magnitude( 0f, float.MaxValue ) ), "Extreme finite inputs must not overflow the force." );
Console.WriteLine( $"PASS: {checks} production blast-impulse checks." );
