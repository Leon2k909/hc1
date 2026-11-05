using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
void Close( float actual, float expected, string message ) => Check( MathF.Abs( actual - expected ) < 0.001f, message );
BarrelHeat Gun() => new() { CoolingTime = 600f, HeatPerShot = 2f, DispersionStart = 200f,
	HotTemperature = 400f, HotDispersion = 2f, CookOffTemperature = 410f, CookOffTime = 10f };
void Drop( BarrelHeat held, DroppedEquipment floor ) => ((IDroppedWeaponState)held).CopyToDroppedWeapon( floor );
void PickUp( BarrelHeat held, DroppedEquipment floor ) => ((IDroppedWeaponState)held).CopyFromDroppedWeapon( floor );

foreach ( var floorSeconds in new[] { 0f, 10f, 180f } )
{
	Time.Now = 0f;
	var source = Gun();
	source.ShotTemperature = 450f;
	source.TimeSinceShot = 0;
	Time.Now = 12f;
	var floor = new DroppedEquipment();
	Drop( source, floor );
	var dropped = floor.GetComponent<BarrelHeat>();
	Close( dropped.Temperature, source.Temperature, "Dropping must preserve current temperature without resetting to cold." );
	Time.Now += floorSeconds;
	var pickup = Gun();
	PickUp( pickup, floor );
	Close( pickup.Temperature, source.Temperature, "Held and dropped guns must cool along the same continuous curve." );
	Close( pickup.Dispersion, source.Dispersion, "Pickup must retain the corresponding hot-barrel dispersion." );
	Check( pickup.CookOffTemperature == 410f && pickup.HeatPerShot == 2f, "Pickup must preserve the recipient prefab's thermal configuration." );
	Close( pickup.TimeSinceShot, 0f, "Pickup temperature must use a fresh clock so elapsed time is not applied twice." );
}

Time.Now = 0;
var original = Gun();
original.ShotTemperature = 300f;
original.TimeSinceShot = 0;
var current = original;
for ( var cycle = 0; cycle < 10; cycle++ )
{
	Time.Now += 3f;
	var floor = new DroppedEquipment();
	Drop( current, floor );
	Time.Now += 7f;
	current = Gun();
	PickUp( current, floor );
}
Close( current.Temperature, original.Temperature, "Repeated drop/pickup cycles must neither erase heat nor add it." );
var beforeShot = current.Temperature;
current.Shoot();
Close( current.Temperature, beforeShot + current.HeatPerShot, "Firing after pickup must add heat to the retained temperature." );

Time.Now = 0;
var hot = Gun();
hot.ShotTemperature = 450f;
hot.TimeSinceShot = 0;
hot.Shoot(); // Deterministic test random chooses a cook-off deadline of 5.5 seconds.
Time.Now = 2f;
var hotFloor = new DroppedEquipment();
Drop( hot, hotFloor );
Time.Now = 3f;
var newOwner = Gun();
PickUp( newOwner, hotFloor );
newOwner.ProbeFixed();
Check( newOwner.Equipment.Bullet.Shots == 0, "Pickup must not prematurely expire an outstanding cook-off deadline." );
Time.Now = 5.6f;
newOwner.ProbeFixed();
Check( newOwner.Equipment.Bullet.Shots == 1, "A hot transferred chamber must retain its existing cook-off deadline." );
hotFloor.GetComponent<BarrelHeat>().ProbeFixed();
Check( hotFloor.GetComponent<BarrelHeat>().Equipment.Bullet.Shots == 0, "Thermal storage on the floor must never run a firing action." );

Time.Now = 6000f;
var cooled = Gun();
PickUp( cooled, hotFloor );
cooled.ProbeFixed();
Check( cooled.Equipment.Bullet.Shots == 0 && cooled.Temperature < cooled.CookOffTemperature,
	"A gun that cooled below the threshold must not cook off merely because its old deadline elapsed." );
var openBolt = Gun();
openBolt.CookOffTemperature = 0f;
openBolt.ShotTemperature = 450f;
openBolt.TimeSinceShot = 0;
var openBoltFloor = new DroppedEquipment();
Drop( openBolt, openBoltFloor );
var openBoltPickup = Gun();
openBoltPickup.CookOffTemperature = 0f;
PickUp( openBoltPickup, openBoltFloor );
openBoltPickup.ProbeFixed();
Check( openBoltPickup.CookOffTemperature == 0f && openBoltPickup.Equipment.Bullet.Shots == 0,
	"A gun configured without cook-off must remain that way after transfer." );

var fresh = Gun();
fresh.ShotTemperature = 17f;
fresh.TimeSinceShot = 0;
PickUp( fresh, new DroppedEquipment() );
Close( fresh.Temperature, 17f, "Legacy/cold drops with no heat state must preserve default initialization." );
Console.WriteLine( $"PASS: {checks} production barrel-heat transfer checks." );

// Engine seams only: real thermal, drop/pickup and cook-off code is linked above.
namespace Facepunch
{
	public class TitleAttribute( string name ) : Attribute { public string Name => name; }
	public class GroupAttribute( string name ) : Attribute { public string Name => name; }
	public class PropertyAttribute : Attribute;
	public class SyncAttribute : Attribute;
	public static class Time { public static float Now; }
	public readonly record struct TimeSince( float Since )
	{
		public static implicit operator TimeSince( float elapsed ) => new( Time.Now - elapsed );
		public static implicit operator float( TimeSince time ) => Time.Now - time.Since;
	}
	public class Component
	{
		public bool IsProxy;
		protected virtual void OnFixedUpdate() { }
		public void ProbeFixed() => OnFixedUpdate();
	}
	public class EquipmentComponent : Component { public Equipment Equipment { get; } = new(); }
	public static class Extensions
	{
		public static bool IsValid( this Component component ) => component is not null;
		public static float Clamp( this float value, float min, float max ) => Math.Clamp( value, min, max );
	}
	public class Equipment : Component
	{
		public bool IsDeployed = true;
		public TagSet Tags = new();
		public Shootable Bullet = new();
		public T GetComponentInChildren<T>() where T : class => Bullet as T;
	}
	public class TagSet { public bool Has( string tag ) => false; }
	public class Shootable : Component
	{
		public Ammo AmmoComponent = new();
		public int Shots;
		public void Shoot() => Shots++;
	}
	public class Ammo : Component { public bool HasAmmo = true; }
	public class DroppedEquipment
	{
		private Component state;
		public T GetOrAddComponent<T>() where T : Component, new() => (T)(state ??= new T());
		public T GetComponent<T>() where T : Component => state as T;
	}
	public interface IDroppedWeaponState
	{
		void CopyToDroppedWeapon( DroppedEquipment dropped );
		void CopyFromDroppedWeapon( DroppedEquipment dropped );
	}
	public static class Game
	{
		public static RandomSource Random = new();
		public class RandomSource { public float Float( float min, float max ) => (min + max) * 0.5f; }
	}
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Zero => default;
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator *( Vector3 a, float n ) => new( a.x * n, a.y * n, a.z * n );
	}
	public readonly record struct Rotation( Vector3 Right, Vector3 Up );
}
