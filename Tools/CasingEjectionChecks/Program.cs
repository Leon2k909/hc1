using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
foreach ( var path in new[] { "weapons/p90/p90.equip", "WEAPONS/P90/P90.EQUIP", "weapons\\p90\\p90.equip" } )
	Check( CasingEjectionRules.EjectsDownward( path ), "The P90 resource must select downward ejection regardless of path case/separators." );
foreach ( var path in new[] { null, "", "weapons/mp5/mp5.equip", "weapons/p90/p90_copy.equip", "weapons/other/p90.equip" } )
	Check( !CasingEjectionRules.EjectsDownward( path ), "Unrecognised weapons must keep conventional ejection." );

foreach ( var side in new[] { 0f, 0.5f, 1f } )
foreach ( var lift in new[] { 0f, 0.5f, 1f } )
foreach ( var rear in new[] { 0f, 0.5f, 1f } )
{
	var p90 = CasingEjectionRules.Sample( "weapons/p90/p90.equip", side, lift, rear );
	Check( p90.Up <= -35f && p90.Up >= -55f && MathF.Abs( p90.Right ) <= 5f && MathF.Abs( p90.Forward ) <= 5f,
		"All P90 launches must leave through a narrow downward cone in weapon space." );
	var legacy = CasingEjectionRules.Sample( null, side, lift, rear );
	Check( legacy.Right == 85f + side * 30f && legacy.Up == 55f + lift * 25f && legacy.Forward == -12f - rear * 18f,
		"Conventional launch distributions must preserve the prior side/up/rear ranges." );
}
foreach ( var value in new[] { float.NaN, float.NegativeInfinity, float.PositiveInfinity, -10f, 10f } )
foreach ( var path in new[] { null, "weapons/p90/p90.equip" } )
{
	var launch = CasingEjectionRules.Sample( path, value, value, value );
	Check( float.IsFinite( launch.Forward ) && float.IsFinite( launch.Right ) && float.IsFinite( launch.Up ),
		"Invalid random samples must never create NaN/infinite casing motion." );
	Check( MathF.Abs( launch.Right ) <= 115f && MathF.Abs( launch.Up ) <= 80f && MathF.Abs( launch.Forward ) <= 30f,
		"Random sample inputs must stay within the authored bounds." );
}
Console.WriteLine( $"PASS: {checks} production casing-ejection checks." );
