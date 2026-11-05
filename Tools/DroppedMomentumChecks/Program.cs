using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
Check( DroppedEquipment.InheritedVelocity( null ) == Vector3.Zero, "Unheld/map-spawned items must have no inherited movement." );
Check( DroppedEquipment.InheritedVelocity( new() ) == Vector3.Zero, "A source with no holder must not invent motion." );
var source = new Equipment { Owner = new() { IsLocallyControlled = true, CharacterController = new() } };
source.Owner.CharacterController.Velocity = new( 250, -75, 140 );
source.Owner.SyncedVelocity = new( 10, 20, 30 );
Check( DroppedEquipment.InheritedVelocity( source ) == new Vector3( 250, -75, 140 ),
	"Local drops must preserve current forward, lateral and vertical movement." );
source.Owner.IsLocallyControlled = false;
Check( DroppedEquipment.InheritedVelocity( source ) == source.Owner.SyncedVelocity,
	"Host drops for remote players must use replicated velocity, not the inactive local controller." );
source.Owner.CharacterController = null;
Check( DroppedEquipment.InheritedVelocity( source ) == source.Owner.SyncedVelocity,
	"A remote drop must work without a local controller." );
source.Owner.IsLocallyControlled = true;
Check( DroppedEquipment.InheritedVelocity( source ) == source.Owner.SyncedVelocity,
	"A missing local controller must fall back to replicated movement." );
foreach ( var velocity in new[] { new Vector3( float.NaN, 0, 0 ), new Vector3( 0, float.PositiveInfinity, 0 ),
	new Vector3( 0, 0, float.NegativeInfinity ) } )
{
	source.Owner.SyncedVelocity = velocity;
	Check( DroppedEquipment.InheritedVelocity( source ) == Vector3.Zero, "Invalid replicated data must never enter physics." );
	source.Owner.CharacterController = new() { Velocity = velocity };
	Check( DroppedEquipment.InheritedVelocity( source ) == Vector3.Zero, "Invalid local data must never enter physics." );
	source.Owner.CharacterController = null;
}
source.Owner.CharacterController = new() { Velocity = Vector3.Zero };
Check( DroppedEquipment.InheritedVelocity( source ) == Vector3.Zero, "A stationary release must remain stationary before any deliberate toss." );
source.Owner.CharacterController.Velocity = new( 0, 0, -350 );
Check( DroppedEquipment.InheritedVelocity( source ).z == -350, "A falling holder's gun must retain its downward velocity." );
Console.WriteLine( $"PASS: {checks} production dropped-weapon momentum checks." );

// Engine seams only; the owner/controller selection and validation above are production code.
namespace Facepunch
{
	public readonly record struct Vector3( float x, float y, float z ) { public static Vector3 Zero => default; }
	public class Component;
	public static class Validity { public static bool IsValid( this Component component ) => component is not null; }
	public class Equipment : Component { public PlayerPawn Owner; }
	public class PlayerPawn : Component
	{
		public bool IsLocallyControlled;
		public Controller CharacterController;
		public Vector3 SyncedVelocity;
	}
	public class Controller : Component { public Vector3 Velocity; }
}
