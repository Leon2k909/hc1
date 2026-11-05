global using Sandbox;
using Facepunch;
using System.Reflection;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var update = typeof( SpectateSystem ).GetMethod( "UpdateSpectate", BindingFlags.NonPublic | BindingFlags.Instance );
var wasSpectating = typeof( SpectateSystem ).GetProperty( "_wasSpectating", BindingFlags.NonPublic | BindingFlags.Instance );
void Step( SpectateSystem system ) => update.Invoke( system, null );

(SpectateSystem System, Client First, Client Second) Setup( bool alreadySpectating = true )
{
	Client.Local = new Client();
	var first = new Client { PlayerPawn = new PlayerPawn() };
	var second = new Client { PlayerPawn = new PlayerPawn() };
	Client.Viewer = first;
	Pawn.Active = first.Pawn;
	var system = new SpectateSystem { FreecamController = new SpectateController() };
	system.Scene.Clients.AddRange( new[] { Client.Local, first, second } );
	wasSpectating.SetValue( system, alreadySpectating );
	return (system, first, second);
}

foreach ( var flags in new[] { (true, false), (false, true), (true, true) } )
{
	Input.Suppressed = flags.Item1;
	GameUtils.MenuOpen = flags.Item2;
	foreach ( var action in new[] { "SpectatorNext", "SpectatorPrev", "SpectatorFreeCam", "SpectatorMode" } )
	{
		var (system, first, second) = Setup();
		Input.Action = action;
		Step( system );
		Check( Client.Viewer == first && !system.IsFreecam && system.CameraMode == CameraMode.FirstPerson,
			"A menu or suppressed input must block next, previous, freecam and view-mode shortcuts." );
		Input.Suppressed = false;
		GameUtils.MenuOpen = false;
		Step( system );
		Check( action switch
		{
			"SpectatorFreeCam" => system.IsFreecam,
			"SpectatorMode" => system.CameraMode == CameraMode.ThirdPerson && first.PlayerPawn.CameraController.Mode == CameraMode.ThirdPerson,
			_ => Client.Viewer == second
		}, "Spectator shortcuts must resume when the UI releases input." );
		Input.Suppressed = flags.Item1;
		GameUtils.MenuOpen = flags.Item2;
	}

	Input.Action = null;
	var missing = Setup();
	missing.First.PlayerPawn = null;
	Step( missing.System );
	Check( Client.Viewer == missing.Second, "A missing followed pawn must still be replaced while a menu is open." );

	var empty = Setup();
	empty.First.PlayerPawn = null;
	empty.Second.PlayerPawn.HealthComponent.State = LifeState.Dead;
	Step( empty.System );
	Check( empty.System.IsFreecam, "Losing the last living candidate must still enter freecam during menu input." );

	var initial = Setup( alreadySpectating: false );
	Step( initial.System );
	Check( Client.Viewer == initial.Second, "Beginning spectating must acquire a target even if UI input is blocked." );
}

Console.WriteLine( $"PASS: {checks} spectator input checks against production SpectateSystem." );

// Minimal engine seams: production code owns input gating, candidate selection, and camera-mode changes.
namespace Sandbox
{
	public sealed class PropertyAttribute : Attribute;
	public class Component { public Scene Scene { get; set; } = new(); protected virtual void OnUpdate() { } }
	public class SingletonComponent<T> : Component;
	public static class Validity { public static bool IsValid( this object value ) => value is not null; }
	public readonly record struct Vector3
	{
		public static Vector3 operator +( Vector3 left, Vector3 right ) => default;
		public static Vector3 operator *( Vector3 vector, float value ) => default;
	}
	public readonly record struct Angles { public Vector3 Forward => default; }
	public readonly record struct Rotation { public Angles Angles() => default; }
	public class GameObject { public Vector3 WorldPosition { get; set; } }
	public class CameraComponent { public Vector3 WorldPosition { get; set; } public Rotation WorldRotation { get; set; } }
	public class Scene
	{
		public List<Client> Clients { get; } = new();
		public CameraComponent Camera { get; set; } = new();
		public IEnumerable<T> GetAllComponents<T>() => Clients.OfType<T>();
	}
	public static class Input
	{
		public static bool Suppressed;
		public static string Action;
		public static bool Pressed( string action ) => action == Action;
	}
}
namespace Facepunch
{
	public enum CameraMode { FirstPerson, ThirdPerson }
	public enum LifeState { Alive, Dead }
	public class HealthComponent { public LifeState State { get; set; } }
	public class CameraController { public CameraMode Mode { get; set; } }
	public static class GameUtils
	{
		public static bool MenuOpen;
		public static bool IsInteractiveMouseUiOpen() => MenuOpen;
	}
	public class Pawn
	{
		public static Pawn Active;
		public bool IsPossessed => Active == this;
		public GameObject GameObject { get; set; } = new();
		public Vector3 WorldPosition { get; set; }
		public Angles EyeAngles { get; set; }
		public void Possess() => Active = this;
	}
	public class PlayerPawn : Pawn
	{
		public HealthComponent HealthComponent { get; set; } = new();
		public CameraController CameraController { get; set; } = new();
	}
	public class SpectateController : Pawn;
	public class Client
	{
		public static Client Local { get; set; }
		public static Client Viewer { get; set; }
		public bool IsConnected { get; set; } = true;
		public bool IsViewer => Viewer == this;
		public bool IsLocalPlayer => Local == this;
		public PlayerPawn PlayerPawn { get; set; }
		public Pawn Pawn => PlayerPawn;
		public void Possess() { Viewer = this; Pawn?.Possess(); }
	}
}
