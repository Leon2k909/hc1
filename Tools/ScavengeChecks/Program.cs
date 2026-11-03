global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var rifle = new EquipmentResource { Category = WeaponCategory.Rifle, Slot = EquipmentSlot.Primary };
var otherRifle = new EquipmentResource { Category = WeaponCategory.Rifle, Slot = EquipmentSlot.Secondary };
var pistol = new EquipmentResource { Category = WeaponCategory.Pistol, Slot = EquipmentSlot.Secondary };
Equipment Held( EquipmentResource resource, int reserve, int max ) => new()
{
	Resource = resource, AmmoState = new WeaponAmmo { Ammo = 12, ReserveAmmo = reserve, MaxReserve = max }
};
DroppedEquipment Drop( int loaded, int reserve ) => new() { Resource = rifle, AmmoState = new WeaponAmmo { Ammo = loaded, ReserveAmmo = reserve } };

var exact = Held( rifle, 0, 50 );
var active = Held( otherRifle, 40, 60 );
var pawn = new PlayerPawn { CurrentEquipment = active };
pawn.Inventory.Equipment.AddRange( [exact, active] );
var drop = Drop( 10, 100 );
Check( drop.FindScavengeTarget( pawn ) == active.AmmoState, "Prefer the compatible weapon in hand over an exact gun match in another slot." );
Check( drop.Scavenge( pawn ), "Compatible guns must scavenge successfully." );
Check( active.AmmoState.ReserveAmmo == 60 && exact.AmmoState.ReserveAmmo == 0, "Only the held gun's reserve must be filled." );
Check( drop.AmmoState.Ammo == 10 && drop.AmmoState.ReserveAmmo == 80, "Take spare rounds before touching the dropped magazine and leave surplus rounds on the ground." );
Check( active.AmmoState.Ammo == 12 && exact.AmmoState.Ammo == 12, "Scavenging must not load the carried magazines for free." );
Check( drop.RoundsLeft + active.AmmoState.ReserveAmmo + exact.AmmoState.ReserveAmmo == 150, "Transferred ammunition must be conserved." );
Check( !drop.Scavenge( pawn ), "Full reserves must not consume more source ammunition." );

exact.AmmoState.ReserveAmmo = 0;
active.AmmoState.ReserveAmmo = 58;
drop = Drop( 5, 0 );
Check( drop.Scavenge( pawn ), "A partly loaded dropped gun must be scavengable." );
Check( active.AmmoState.ReserveAmmo == 60 && exact.AmmoState.ReserveAmmo == 0, "There must be no spillover into holstered guns." );
Check( drop.AmmoState.Ammo == 3 && drop.AmmoState.ReserveAmmo == 0, "Unused loaded rounds must stay in the dropped gun." );
Check( !drop.Scavenge( pawn ) && exact.AmmoState.ReserveAmmo == 0, "Full held reserves must not redirect later contacts into another gun." );
active.AmmoState.ReserveAmmo = 0;
drop = Drop( 5, 0 );
Check( drop.Scavenge( pawn ) && drop.AmmoState.Ammo == 1 && active.AmmoState.ReserveAmmo == 4, "Always leave the dropped gun's last loaded round." );

pawn.CurrentEquipment = Held( pistol, 0, 20 );
active.AmmoState.ReserveAmmo = 0;
Check( Drop( 2, 0 ).FindScavengeTarget( pawn ) is null, "An incompatible held gun must not redirect scavenging to a compatible holstered gun." );

var pistolPawn = new PlayerPawn();
var pistolHeld = Held( pistol, 0, 20 );
pistolPawn.Inventory.Equipment.Add( pistolHeld );
pistolPawn.CurrentEquipment = pistolHeld;
drop = Drop( 8, 10 );
Check( !drop.Scavenge( pistolPawn ) && drop.RoundsLeft == 18, "Incompatible categories must not share ammunition." );

exact.AmmoState.ReserveAmmo = 49;
active.AmmoState.ReserveAmmo = 59;
pawn.CurrentEquipment = active;
drop = Drop( 0, 4 );
Check( drop.Scavenge( pawn ), "An empty dropped magazine can still supply spare rounds." );
Check( active.AmmoState.ReserveAmmo == 60 && exact.AmmoState.ReserveAmmo == 49 && drop.RoundsLeft == 3,
	"Reserve caps must be respected and surplus rounds remain on the ground." );

exact.AmmoState.ReserveAmmo = 70;
active.AmmoState.ReserveAmmo = 0;
drop = Drop( 1, 3 );
Check( drop.Scavenge( pawn ) && exact.AmmoState.ReserveAmmo == 70 && active.AmmoState.ReserveAmmo == 3,
	"Skip overfull reserves without subtracting ammunition." );
Check( drop.AmmoState.Ammo == 1, "Preserve the last loaded round even after spare rounds are depleted." );
Check( !Drop( 5, 10 ).Scavenge( null ), "Missing players must not consume ammunition." );
var missingResource = Drop( 5, 10 );
missingResource.Resource = null;
Check( !missingResource.Scavenge( pawn ), "Incomplete dropped resources must fail safely." );
var noAmmo = new DroppedEquipment { Resource = rifle };
Check( !noAmmo.Scavenge( pawn ), "Objects without an ammunition component must fail safely." );

// A spread of source and reserve counts verifies conservation and caps without depending on one example.
foreach ( var loaded in new[] { 0, 1, 7, 30 } )
foreach ( var spare in new[] { 0, 3, 100 } )
foreach ( var initial in new[] { 0, 45, 50 } )
{
	var a = Held( rifle, initial, 50 );
	var b = Held( otherRifle, initial, 50 );
	var player = new PlayerPawn { CurrentEquipment = b };
	player.Inventory.Equipment.AddRange( [a, b] );
	var source = Drop( loaded, spare );
	var before = source.RoundsLeft + a.AmmoState.ReserveAmmo + b.AmmoState.ReserveAmmo;
	source.Scavenge( player );
	Check( before == source.RoundsLeft + a.AmmoState.ReserveAmmo + b.AmmoState.ReserveAmmo, "Every transfer conserves rounds." );
	Check( a.AmmoState.ReserveAmmo <= 50 && b.AmmoState.ReserveAmmo <= 50, "Every transfer respects both reserve caps." );
	Check( a.AmmoState.ReserveAmmo == initial, "Every transfer leaves holstered ammunition unchanged." );
	Check( source.AmmoState.Ammo >= Math.Min( loaded, 1 ) && source.AmmoState.ReserveAmmo >= 0, "Every transfer preserves the final round and non-negative spare ammo." );
}

Console.WriteLine( $"PASS: {checks} ammo scavenging checks against production scavenging code." );

// Engine seams only: the linked production partial owns ordering and every ammunition transfer.
namespace Sandbox
{
	public class Component { public bool Valid { get; set; } = true; }
	public static class Validity { public static bool IsValid( this Component component ) => component?.Valid == true; }
}
namespace Facepunch
{
	public enum WeaponCategory { Rifle, Pistol }
	public enum EquipmentSlot { Primary, Secondary }
	public class EquipmentResource { public WeaponCategory Category; public EquipmentSlot Slot; }
	public class WeaponAmmo : Component
	{
		public int Ammo, ReserveAmmo, MaxReserve;
		public int GetMaxReserve() => MaxReserve;
		public void ReceiveReserve( int rounds ) => ReserveAmmo += Math.Clamp( rounds, 0, Math.Max( 0, MaxReserve - ReserveAmmo ) );
	}
	public class Equipment : Component
	{
		public EquipmentResource Resource;
		public WeaponAmmo AmmoState;
		public T GetComponentInChildren<T>( bool includeDisabled ) where T : class => AmmoState as T;
	}
	public class PlayerInventory { public List<Equipment> Equipment { get; } = new(); }
	public class PlayerPawn : Component { public PlayerInventory Inventory { get; } = new(); public Equipment CurrentEquipment; }
	public partial class DroppedEquipment : Component
	{
		public EquipmentResource Resource;
		public WeaponAmmo AmmoState;
		public int RoundsLeft => AmmoState is { } ammo ? ammo.Ammo + ammo.ReserveAmmo : 0;
		public T GetComponent<T>() where T : class => AmmoState as T;
		public bool Scavenge( PlayerPawn player ) => TryScavenge( player );
	}
}
