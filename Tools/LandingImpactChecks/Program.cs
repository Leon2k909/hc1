using Facepunch;

var checks = 0;
void Check( bool ok, string message )
{
	checks++;
	if ( !ok ) throw new Exception( message );
}
foreach ( var speed in new[] { 0f, 100f, 300f, 600f, 1000f } )
{
	Check( LandingImpactRules.ClosingSpeed( -speed, 0 ) == speed, "Static-floor falling speed preserved" );
	Check( LandingImpactRules.ClosingSpeed( speed, 0 ) == 0, "Upward movement is not a downward impact" );
	Check( LandingImpactRules.ClosingSpeed( -speed, -speed ) == 0, "Matching downward motion has no impact" );
	Check( LandingImpactRules.ClosingSpeed( speed, speed ) == 0, "Matching upward motion has no impact" );
}
Check( LandingImpactRules.ClosingSpeed( -600, -200 ) == 400, "Descending surface softens landing" );
Check( LandingImpactRules.ClosingSpeed( -600, 200 ) == 800, "Rising surface increases closing speed" );
Check( LandingImpactRules.ClosingSpeed( 100, 200 ) == 100, "Surface rising faster than player can hit the boots" );
Check( LandingImpactRules.ClosingSpeed( -200, -600 ) == 0, "Surface falling away cannot cause landing damage" );
foreach ( var invalid in new[] { float.NaN, float.PositiveInfinity, float.NegativeInfinity } )
{
	Check( LandingImpactRules.ClosingSpeed( invalid, 0 ) == 0, "Invalid player motion is harmless" );
	Check( LandingImpactRules.ClosingSpeed( -300, invalid ) == 300, "Invalid ground velocity falls back to static ground" );
}
Check( LandingImpactRules.ClosingSpeed( -float.MaxValue, float.MaxValue ) == float.MaxValue,
	"Extreme closing speed stays finite" );

var pawn = new PlayerPawn { PreviousVelocity = new( 100, 200, -600 ), WorldPosition = new( 1, 2, 3 ) };
Check( pawn.LandingImpactSpeed() == 600, "Missing ground collider uses static-floor fallback" );
var collider = pawn.CharacterController.GroundCollider = new Collider { Velocity = new( 0, 0, -200 ) };
Check( pawn.LandingImpactSpeed() == 400, "Pawn uses actual ground point velocity" );
Check( collider.LastPoint == pawn.WorldPosition, "Ground velocity sampled at the boots" );
collider.Velocity = new( 900, -700, -200 );
Check( pawn.LandingImpactSpeed() == 400, "Horizontal motion cannot manufacture a vertical impact" );
collider.Velocity = new( 0, 0, 200 );
Check( pawn.LandingImpactSpeed() == 800, "Pawn integration handles upward ground velocity" );
Console.WriteLine( $"Passed {checks} production landing impact checks." );

namespace Facepunch
{
	public readonly record struct Vector3( float x, float y, float z );
	public static class Validity { public static bool IsValid( this object value ) => value is not null; }
	public class Collider
	{
		public Vector3 Velocity { get; set; }
		public Vector3 LastPoint { get; private set; }
		public Vector3 GetVelocityAtPoint( Vector3 point ) { LastPoint = point; return Velocity; }
	}
	public class CharacterController { public Collider GroundCollider { get; set; } }
	public partial class PlayerPawn
	{
		private Vector3 _previousVelocity;
		public Vector3 PreviousVelocity { set => _previousVelocity = value; }
		public Vector3 WorldPosition { get; set; }
		public CharacterController CharacterController { get; } = new();
	}
}
