global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
TestThrowable Prepare( bool release )
{
	Clock.Now = 0;
	Input.Held = false;
	Input.CancelPressed = false;
	var throwable = new TestThrowable();
	throwable.Fixed();
	Input.Held = true;
	throwable.Fixed();
	Check( throwable.ThrowState == Throwable.State.Cook, "An ordinary press must start preparation." );
	Clock.Now = .3f;
	if ( release ) { Input.Held = false; throwable.Fixed(); }
	return throwable;
}

var blocks = new (string Name, Action<TestThrowable, bool> Set)[]
{
	("class menu", (_, value) => Facepunch.UI.ClassSelect.IsAnyOpen = value),
	("buy menu", (_, value) => Facepunch.UI.TacticalBuyMenu.IsAnyOpen = value),
	("workbench", (_, value) => Facepunch.UI.ZombiesWorkbenchPanel.IsAnyOpen = value),
	("gunsmith", (_, value) => GameUtils.GunsmithOpen = value),
	("pause", (_, value) => Input.Suppressed = value),
	("menu cursor", (_, value) => Input.MouseCursorVisible = value),
	("death", (item, value) => item.Owner.HealthComponent.State = value ? LifeState.Dead : LifeState.Alive),
	("frozen", (item, value) => item.Owner.IsFrozen = value),
	("climbing", (item, value) => item.Owner.IsPipeClimbing = value),
	("mantling", (item, value) => item.Owner.IsMantling = value),
	("holstering", (item, value) => item.Weapon.IsDeployed = !value)
};

foreach ( var block in blocks )
foreach ( var released in new[] { false, true } )
{
	var item = Prepare( released );
	block.Set( item, true );
	Clock.Now += .2f;
	item.Update(); // Test the frame update before fixed input suppression gets another turn.
	Check( item.ThrowState == Throwable.State.Idle && item.Projectiles == 0, $"{block.Name}: both preparation stages must cancel before releasing a projectile." );
	block.Set( item, false );
	Clock.Now += 1;
	item.Update();
	Check( item.Projectiles == 0, $"{block.Name}: cancelled preparations must not resume automatically." );
}

var normal = Prepare( release: true );
Clock.Now += .2f;
normal.Update();
Check( normal.Projectiles == 1 && normal.ThrowState == Throwable.State.Thrown, "An uninterrupted throw must release exactly one projectile." );
Facepunch.UI.ClassSelect.IsAnyOpen = true;
normal.Fixed();
Check( normal.ThrowState == Throwable.State.Thrown, "Opening a menu must not undo an already released grenade." );
Facepunch.UI.ClassSelect.IsAnyOpen = false;
Clock.Now += .3f;
normal.Update();
Check( normal.Owner.Inventory.Removed == 1 && normal.Projectiles == 1, "The host must still remove a successfully thrown item." );

var suppressed = Prepare( release: false );
Facepunch.UI.ClassSelect.IsAnyOpen = true;
suppressed.Fixed();
Check( suppressed.ThrowState == Throwable.State.Idle, "Fixed input suppression must cancel rather than convert the forced release into a throw." );
Facepunch.UI.ClassSelect.IsAnyOpen = false;
var cancel = Prepare( release: false );
Input.CancelPressed = true;
cancel.Update();
Check( cancel.ThrowState == Throwable.State.Idle && cancel.Projectiles == 0, "Secondary-attack cancellation must remain supported." );

var actual = new TestThrowable { Prefab = new() };
actual.Owner.AimRay = new( new( 0, 0, 64 ), new( 1, 0, 0 ) );
actual.Owner.CharacterController.Velocity = new( 100, 20, 0 );
actual.SpawnActual();
Check( GameObject.LastClone.Position == new Vector3( 32, -10, 64 ), "An unobstructed throw must retain its existing release position." );
Check( actual.Scene.Trace.Start == actual.Owner.AimRay.Position && actual.Scene.Trace.End == new Vector3( 32, -10, 64 ),
	"Clearance must sweep the entire forward and sideways offset." );
Check( actual.Scene.Trace.Radius == 2f, "Clearance must account for projectile width rather than using a zero-width line." );
Check( actual.Scene.Trace.Ignored == actual.GameObject.Root, "The clearance probe must ignore the thrower's own hierarchy." );
Check( actual.Scene.Trace.Excluded.SequenceEqual( new[] { "trigger", "playerclip", "movement" } ),
	"Invisible movement/trigger volumes must not obstruct a grenade's release." );
var launched = GameObject.LastClone.GetComponentInChildren<Rigidbody>();
Check( launched.Velocity == new Vector3( 100 + actual.ThrowPower, 20, 100 ), "Throw velocity must retain both inherited movement and authored throw power." );

foreach ( var contact in new[] { new Vector3( 18, -5.625f, 64 ), new Vector3( 5, -1.5625f, 64 ), new Vector3( 0, 0, 64 ) } )
{
	actual.Scene.Trace.Result = new() { Hit = true, EndPosition = contact, HitPosition = new( 99, 99, 99 ), Normal = new( -1, 0, 0 ) };
	actual.SpawnActual();
	Check( GameObject.LastClone.Position == contact, "Obstructed throws must use the swept centre, with no unchecked sideways offset or oversized normal push." );
	Check( GameObject.LastClone.GetComponent<BaseGrenade>().Player == actual.Owner, "Obstruction must preserve grenade attribution." );
}

Console.WriteLine( $"PASS: {checks} throwable checks against production input, release and clearance code." );

// Input and engine services are isolated; production code owns preparation, cancellation and release timing.
namespace Sandbox
{
	public static class Clock { public static float Now; }
	public readonly record struct TimeSince( float Started )
	{
		public static implicit operator TimeSince( float elapsed ) => new( Clock.Now - elapsed );
		public static bool operator >( TimeSince time, float seconds ) => Clock.Now - time.Started > seconds;
		public static bool operator <( TimeSince time, float seconds ) => Clock.Now - time.Started < seconds;
	}
	public class Component
	{
		public bool IsProxy;
		public GameObject GameObject { get; } = new();
		public Scene Scene { get; } = new();
		public NetworkState Network { get; } = new();
		protected virtual void OnUpdate() { }
		protected virtual void OnFixedUpdate() { }
	}
	public static class Validity { public static bool IsValid( this Component component ) => component is not null; }
	public sealed class PropertyAttribute : Attribute;
	public sealed class SyncAttribute : Attribute;
	public sealed class TitleAttribute( string title ) : Attribute { public string Title => title; }
	public sealed class GroupAttribute( string group ) : Attribute { public string Group => group; }
	public sealed class CategoryAttribute( string category ) : Attribute { public string Category => category; }
	public static class Networking { public static bool IsHost => true; }
	public class Connection { public static Connection Host { get; } = new(); }
	public static class Rpc
	{
		public static Connection Caller => null;
		public sealed class OwnerAttribute : Attribute;
		public sealed class BroadcastAttribute : Attribute;
	}
	public enum NetworkOrphaned { ClearOwner }
	public class NetworkState { public Connection Owner => Connection.Host; public void SetOrphanedMode( NetworkOrphaned mode ) { } }
	public static class Input
	{
		public static bool Held, CancelPressed, Suppressed, MouseCursorVisible;
		public static bool Down( string action ) => action.Equals( "Attack1", StringComparison.OrdinalIgnoreCase ) && Held;
		public static bool Pressed( string action ) => action.Equals( "Attack2", StringComparison.OrdinalIgnoreCase ) && CancelPressed;
	}
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Up => new( 0, 0, 1 );
		public static Vector3 Random => default;
		public float Length => MathF.Sqrt( x * x + y * y + z * z );
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator *( Vector3 a, float scale ) => new( a.x * scale, a.y * scale, a.z * scale );
	}
	public readonly record struct Ray( Vector3 Position, Vector3 Forward );
	public readonly record struct Rotation
	{
		public Vector3 Right => new( 0, -1, 0 );
		public static Rotation From( float pitch, float yaw, float roll ) => default;
	}
	public readonly record struct Angles( float yaw ) { public Rotation ToRotation() => default; }
	public class Model { public Bounds Bounds { get; } = new(); }
	public class Bounds { public Vector3 Size => new( 1, 1, 1 ); }
	public class Renderer : Component { public void SetBool( string name, bool value ) { } }
	public class Rigidbody : Component { public Vector3 Velocity, AngularVelocity; }
	public class GameObject
	{
		public static GameObject LastClone;
		public Vector3 Position;
		private readonly Dictionary<Type, object> components = new();
		public GameObject Root => this;
		public NetworkState Network { get; } = new();
		public Tags Tags { get; } = new();
		public GameObject Clone( Vector3 position, Rotation rotation ) => LastClone = new() { Position = position };
		public T GetComponent<T>() where T : new()
		{
			if ( !components.TryGetValue( typeof(T), out var component ) ) components[typeof(T)] = component = new T();
			return (T)component;
		}
		public T GetComponentInChildren<T>() where T : new() => GetComponent<T>();
		public void NetworkSpawn() { }
		public Team GetTeam() => default;
	}
	public class Tags { public void Set( string name, bool value ) { } }
	public class Scene { public TraceStub Trace { get; } = new(); }
	public class TraceStub
	{
		public Vector3 Start, End;
		public float Radius;
		public GameObject Ignored;
		public string[] Excluded;
		public TraceResult? Result;
		public TraceStub Ray( Ray ray, float distance ) => this;
		public TraceStub Sphere( float radius, Vector3 from, Vector3 to ) { Radius = radius; Start = from; End = to; return this; }
		public TraceStub IgnoreGameObjectHierarchy( GameObject obj ) { Ignored = obj; return this; }
		public TraceStub WithoutTags( params string[] tags ) { Excluded = tags; return this; }
		public TraceResult Run() => Result ?? new TraceResult { EndPosition = End };
	}
	public struct TraceResult { public bool Hit; public Vector3 HitPosition, EndPosition, Normal; }
}
namespace Sandbox.Events { public interface IGameEventHandler<T> { void OnGameEvent( T args ); } }
namespace Facepunch
{
	public enum LifeState { Alive, Dead }
	public enum Team { Unassigned }
	public enum RadioSound { ThrownGrenade }
	public class HealthComponent { public LifeState State { get; set; } = LifeState.Alive; }
	public class PlayerInventory { public int Removed; public void RemoveWeapon( Equipment item ) => Removed++; }
	public class PlayerPawn : Component
	{
		public bool IsFrozen, IsPipeClimbing, IsMantling;
		public bool IsLocallyControlled => true;
		public HealthComponent HealthComponent { get; } = new();
		public PlayerInventory Inventory { get; } = new();
		public Renderer BodyRenderer { get; } = new();
		public Rigidbody CharacterController { get; } = new();
		public Ray AimRay { get; set; }
		public Angles EyeAngles => default;
	}
	public class EquipmentResource { public Model WorldModel { get; } = new(); }
	public class Equipment : Component { public bool IsDeployed = true; public PlayerPawn Owner { get; } = new(); public EquipmentResource Resource { get; } = new(); }
	public abstract class EquipmentComponent : Component { protected Equipment Equipment { get; } = new(); }
	public sealed class EquipmentResourcePropertyAttribute : Attribute;
	public record EquipmentDeployedEvent( Equipment Equipment );
	public record EquipmentHolsteredEvent;
	public class BaseGrenade : Component { public PlayerPawn Player; public string SkinId; }
	public class Skin { public string Id => ""; }
	public static class EquipmentSkins { public static Skin SkinOf( EquipmentResource resource, PlayerPawn player ) => null; }
	public static class RadioSounds { public static void Play( Team team, RadioSound sound ) { } }
	public static class GameUtils { public static bool GunsmithOpen; public static bool IsGunsmithStudioOpen() => GunsmithOpen; }
	public sealed class TestThrowable : Throwable
	{
		public int Projectiles;
		public PlayerPawn Owner => Equipment.Owner;
		public Equipment Weapon => Equipment;
		public void Fixed() => base.OnFixedUpdate();
		public void Update() => base.OnUpdate();
		public void SpawnActual() => base.SpawnProjectile( Owner );
		protected override void SpawnProjectile( PlayerPawn player ) => Projectiles++;
	}
}
namespace Facepunch.UI
{
	public static class ClassSelect { public static bool IsAnyOpen; }
	public static class TacticalBuyMenu { public static bool IsAnyOpen; }
	public static class ZombiesWorkbenchPanel { public static bool IsAnyOpen; }
}
