global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}

SceneTraceResult Hit( float distance, Component target = null, bool trigger = false )
{
	var obj = new GameObject { Target = target };
	if ( target is not null ) target.GameObject = obj;
	return new SceneTraceResult { Distance = distance, GameObject = obj, Collider = new Collider { IsTrigger = trigger } };
}

void Scenario( string name, SceneTraceResult[] hits, IUse expected )
{
	var pawn = new PlayerPawn();
	pawn.Scene.Trace.Hits = hits;
	Input.IsPressed = false;
	pawn.TickUse();
	Check( pawn.Hovered == expected, $"{name}: hover must select the nearest reachable usable." );
	var before = hits.Select( x => x.GameObject?.Target ).OfType<TestUsable>().ToDictionary( x => x, x => x.Uses );
	pawn.DevUse();
	foreach ( var pair in before )
		Check( pair.Key.Uses == pair.Value + (pair.Key == expected ? 1 : 0), $"{name}: Use must affect only the reachable target." );
	Check( pawn.Scene.UseEvents == (expected is null ? 0 : 1), $"{name}: blocked interactions must not dispatch use events." );
}

var behindWall = new TestUsable();
Scenario( "Solid wall before target", [Hit( 40, behindWall ), Hit( 20 )], null );
var first = new TestUsable();
var second = new TestUsable();
Scenario( "Nearest of two targets", [Hit( 60, second ), Hit( 20, first )], first );
var throughTrigger = new TestUsable();
Scenario( "Non-interactive trigger before target", [Hit( 10, trigger: true ), Hit( 30, throughTrigger )], throughTrigger );
var triggerTarget = new TestUsable();
Scenario( "Interactive trigger before wall", [Hit( 30 ), Hit( 10, triggerTarget, trigger: true )], triggerTarget );
var blockedTrigger = new TestUsable();
Scenario( "Interactive trigger behind wall", [Hit( 20 ), Hit( 40, blockedTrigger, trigger: true )], null );
var beforeWall = new TestUsable();
Scenario( "Target before wall", [Hit( 50 ), Hit( 10, beforeWall )], beforeWall );
Scenario( "No hits", [], null );
var noCollider = Hit( 10 );
noCollider.Collider = null;
Scenario( "World geometry without collider component", [noCollider, Hit( 20, new TestUsable() )], null );
var noObject = Hit( 10 );
noObject.GameObject = null;
Scenario( "World geometry without a game object", [noObject, Hit( 20, new TestUsable() )], null );
var invalid = new TestUsable { Valid = false };
Scenario( "Invalid usable cannot expose a target behind it", [Hit( 10, invalid ), Hit( 20, new TestUsable() )], null );

// A refused use must still show its existing reason and must not use the object behind it.
var refused = new TestUsable { Allowed = false };
var hidden = new TestUsable();
var refusingPawn = new PlayerPawn();
refusingPawn.Scene.Trace.Hits = [Hit( 10, refused ), Hit( 20, hidden )];
refusingPawn.DevUse();
Check( refused.Uses == 0 && hidden.Uses == 0 && GameMode.Instance.Toasts == 1, "Refused interactions must preserve their feedback without reaching through the object." );

Console.WriteLine( $"PASS: {checks} interaction checks against production PlayerPawn.Using.cs." );

// Only world data and engine services are supplied here. Target selection, hover, and Use execute production code.
namespace Sandbox
{
	public interface IValid { bool IsValid { get; } }
	public static class Validity { public static bool IsValid( this IValid value ) => value?.IsValid == true; }
	public class Component : IValid
	{
		public bool Valid { get; set; } = true;
		bool IValid.IsValid => Valid;
		public GameObject GameObject { get; set; } = new();
	}
	public class Collider : Component { public bool IsTrigger { get; set; } }
	public class GameObject : IValid
	{
		public bool IsValid => true;
		public Component Target { get; set; }
		public T GetComponentInParent<T>() where T : class => Target as T;
	}
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Zero => default;
		public float Length => MathF.Sqrt( x * x + y * y + z * z );
		public Vector3 Normal => Length > 0 ? new( x / Length, y / Length, z / Length ) : default;
		public float Dot( Vector3 other ) => x * other.x + y * other.y + z * other.z;
		public static Vector3 operator -( Vector3 a, Vector3 b ) => new( a.x - b.x, a.y - b.y, a.z - b.z );
	}
	public readonly record struct Ray( Vector3 Position, Vector3 Forward );
	public struct SceneTraceResult { public float Distance; public GameObject GameObject; public Component Collider; public bool Hit; }
	public class Scene
	{
		public TraceStub Trace { get; } = new();
		public int UseEvents;
		public IEnumerable<T> GetAllComponents<T>() => [];
		public void Dispatch( object args ) => UseEvents++;
	}
	public class TraceStub
	{
		public SceneTraceResult[] Hits { get; set; } = [];
		public TraceStub Ray( Ray ray, float distance ) => this;
		public TraceStub Ray( Vector3 from, Vector3 to ) => this;
		public TraceStub Size( float size ) => this;
		public TraceStub IgnoreGameObjectHierarchy( GameObject obj ) => this;
		public TraceStub HitTriggers() => this;
		public TraceStub WithoutTags( params string[] tags ) => this;
		public SceneTraceResult[] RunAll() => Hits;
		public SceneTraceResult Run() => default;
	}
	public sealed class PropertyAttribute : Attribute;
	public sealed class SyncAttribute : Attribute;
	public sealed class GroupAttribute( string group ) : Attribute { public string Group => group; }
	public static class Input { public static bool IsPressed; public static bool Pressed( string action ) => IsPressed; public static bool Down( string action ) => IsPressed; }
	public class Connection { public static Connection Host { get; } = new(); }
	public class NetworkState { public Connection Owner { get; } = new(); }
	public enum NetFlags { HostOnly }
	public static class Rpc
	{
		public sealed class OwnerAttribute : Attribute;
		public sealed class BroadcastAttribute( NetFlags flags ) : Attribute { public NetFlags Flags => flags; }
		public static IDisposable FilterInclude( Connection connection ) => new Filter();
		private class Filter : IDisposable { public void Dispose() { } }
	}
}
namespace Sandbox.Events { public interface IGameEvent; }
namespace Facepunch
{
	public enum Team { Unassigned, Terrorist }
	public enum EquipmentSlot { Special }
	public class BombSite;
	public static class ReconOctocopter { public static bool JustUnlinked => false; }
	public partial class PlayerPawn : Component
	{
		public Scene Scene { get; } = new();
		public Ray AimRay => new( default, new Vector3( 1, 0, 0 ) );
		public bool IsPipeClimbing, IsPilotingDrone;
		public Team Team { get; set; }
		public NetworkState Network { get; } = new();
		public TestInventory Inventory { get; } = new();
		public T GetZone<T>() where T : class => null;
		public void StopPipeClimb( Vector3 velocity ) { }
		public void TickUse() => UpdateUse();
	}
	public class TestInventory { public void SwitchToSlot( EquipmentSlot slot ) { } }
	public class TestUsable : Component, IUse
	{
		public int Uses;
		public bool Allowed { get; set; } = true;
		public UseResult CanUse( PlayerPawn player ) => Allowed ? (UseResult)true : "Cannot use";
		public void OnUse( PlayerPawn player ) => Uses++;
	}
	public class DroppedEquipment : TestUsable { public Vector3 Center => default; }
	public class GameMode
	{
		public static GameMode Instance { get; } = new();
		public int Toasts;
		public void ShowToast( string text, UI.ToastType type, float seconds ) => Toasts++;
	}
}
namespace Facepunch.UI { public enum ToastType { Generic } }
