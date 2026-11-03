global using Sandbox;
using Facepunch;
using System.Reflection;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var flags = BindingFlags.Instance | BindingFlags.NonPublic;
var playerProperty = typeof( PlayerPingComponent ).GetProperty( "Player", flags );
var pingProperty = typeof( PlayerPingComponent ).GetProperty( "WorldPing", flags );
var tick = typeof( PlayerPingComponent ).GetMethod( "OnUpdate", flags );
PlayerPingComponent Controller( PlayerPawn player, WorldPingComponent ping )
{
	var controller = new PlayerPingComponent();
	playerProperty.SetValue( controller, player );
	pingProperty.SetValue( controller, ping );
	return controller;
}
void Step( PlayerPingComponent controller ) => tick.Invoke( controller, null );
WorldPingComponent Marker( Vector3 position ) => new() { WorldPosition = position };

Input.PingPressed = true;
var player = new PlayerPawn();
var marker = Marker( new Vector3( 100, 0, -32 ) );
var controller = Controller( player, marker );
Step( controller );
Check( marker.GameObject.Destroyed, "A visible world ping against the sky must be removable." );
Check( controller.Scene.Trace.Runs == 0, "Removing an existing ping must not require a world trace." );

var receiver = new TestReceiver { Position = new Vector3( 100, 0, 0 ) };
marker = Marker( new Vector3( 100, 100, 0 ) );
marker.Receiver = receiver;
controller = Controller( player, marker );
Step( controller );
Check( marker.GameObject.Destroyed && receiver.Cancels == 1, "Cancellation must use a moving receiver's current displayed position and notify it." );

marker = Marker( new Vector3( 100, 0, 0 ) );
receiver = new TestReceiver { Position = new Vector3( 100, 100, 0 ) };
marker.Receiver = receiver;
controller = Controller( player, marker );
Step( controller );
Check( !marker.GameObject.Destroyed && receiver.Cancels == 0, "Looking at the target's old position must not cancel its moved marker." );
Check( controller.Scene.Trace.Runs == 1, "A placement attempt must use only one trace." );

marker = Marker( new Vector3( 0, 100, 0 ) );
controller = Controller( player, marker );
controller.Scene.Trace.Result = new SceneTraceResult { Hit = true, EndPosition = new Vector3( 200, 0, 0 ) };
Step( controller );
var replacement = (WorldPingComponent)pingProperty.GetValue( controller );
Check( marker.GameObject.Destroyed && replacement != marker && replacement.WorldPosition == new Vector3( 200, 0, 0 ),
	"Pinging a different location must still replace the old ping." );
Check( controller.Scene.Trace.Runs == 1, "Successful placement must not repeat the trace." );

foreach ( var blocked in new[] { "dead", "drone", "remote", "no press" } )
{
	var pawn = new PlayerPawn { IsLocallyControlled = blocked != "remote", IsPilotingDrone = blocked == "drone" };
	pawn.HealthComponent.State = blocked == "dead" ? LifeState.Dead : LifeState.Alive;
	Input.PingPressed = blocked != "no press";
	marker = Marker( new Vector3( 100, 0, -32 ) );
	controller = Controller( pawn, marker );
	Step( controller );
	Check( !marker.GameObject.Destroyed && controller.Scene.Trace.Runs == 0, $"{blocked}: unavailable ping controls must not modify markers or trace the world." );
}

Console.WriteLine( $"PASS: {checks} ping input checks against production PlayerPingComponent." );

namespace Sandbox
{
	public interface IValid { bool IsValid { get; } }
	public static class Validity { public static bool IsValid( this IValid value ) => value?.IsValid == true; public static bool AlmostEqual( this float a, float b, float epsilon ) => MathF.Abs( a - b ) <= epsilon; }
	public class Component : IValid
	{
		protected virtual void OnUpdate() { }
		public GameObject GameObject { get; set; } = new();
		bool IValid.IsValid => !GameObject.Destroyed;
		public Scene Scene { get; } = new();
		public Vector3 WorldPosition { get => GameObject.WorldPosition; set => GameObject.WorldPosition = value; }
	}
	public class GameObject : IValid
	{
		public bool Destroyed;
		public bool IsValid => !Destroyed;
		public Vector3 WorldPosition;
		public string Name;
		public GameObject Root => this;
		public TransformState Transform { get; } = new();
		public ComponentStore Components => new( this );
		public void Destroy() => Destroyed = true;
		public T GetComponent<T>() where T : class => null;
	}
	public class ComponentStore( GameObject owner ) { public T Create<T>() where T : Component, new() => new() { GameObject = owner }; }
	public class TransformState { public void ClearInterpolation() { } }
	public sealed class RequireComponentAttribute : Attribute;
	public sealed class PropertyAttribute : Attribute;
	public static class Rpc { public sealed class OwnerAttribute : Attribute; }
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Up => new( 0, 0, 1 );
		public Vector3 Normal { get { var length = MathF.Sqrt( Dot( this, this ) ); return length > 0 ? new( x / length, y / length, z / length ) : default; } }
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator -( Vector3 a, Vector3 b ) => new( a.x - b.x, a.y - b.y, a.z - b.z );
		public static Vector3 operator *( Vector3 a, float b ) => new( a.x * b, a.y * b, a.z * b );
		public static float Dot( Vector3 a, Vector3 b ) => a.x * b.x + a.y * b.y + a.z * b.z;
	}
	public readonly record struct Color;
	public readonly record struct Ray;
	public class Rotation { public Vector3 Forward => new( 1, 0, 0 ); }
	public class CameraComponent : Component { public Rotation WorldRotation { get; } = new(); }
	public struct SceneTraceResult { public bool Hit; public Vector3 EndPosition; public GameObject GameObject; }
	public class Scene { public TraceStub Trace { get; } = new(); }
	public class TraceStub
	{
		public int Runs;
		public SceneTraceResult Result;
		public TraceStub Ray( Ray ray, float distance ) => this;
		public TraceStub IgnoreGameObjectHierarchy( GameObject obj ) => this;
		public SceneTraceResult Run() { Runs++; return Result; }
	}
	public static class Input { public static bool PingPressed; public static bool Pressed( string action ) => PingPressed; }
}
namespace Facepunch
{
	public enum LifeState { Alive, Dead }
	public class Client { public string DisplayName => "Player"; }
	public class HealthComponent : Component { public LifeState State { get; set; } = LifeState.Alive; }
	public class CameraController { public CameraComponent Camera { get; } = new(); }
	public class PlayerPawn : Component
	{
		public bool IsLocallyControlled { get; set; } = true;
		public bool IsPilotingDrone;
		public Client Client { get; } = new();
		public HealthComponent HealthComponent { get; } = new();
		public Ray AimRay => default;
		public CameraController CameraController { get; } = new();
	}
	public interface IMarkerObject { Vector3 MarkerPosition { get; } }
	public class WorldPingComponent : Component, IMarkerObject
	{
		public Client Owner;
		public IPingReceiver Receiver;
		public Component Target { set => Receiver = value as IPingReceiver; }
		Vector3 IMarkerObject.MarkerPosition => Receiver.IsValid() ? Receiver.Position : WorldPosition + Vector3.Up * 32;
		public void Trigger( float lifetime ) => Receiver?.OnPing();
	}
	public class TestReceiver : Component, IPingReceiver
	{
		public Vector3 Position { get; set; }
		public int Cancels;
		public void OnPingCancel() => Cancels++;
	}
	public static class NetworkUtils
	{
		public static IDisposable RpcMyTeam() => new Filter();
		private class Filter : IDisposable { public void Dispose() { } }
	}
}
