global using Sandbox;
using Facepunch;
using System.Reflection;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
void Near( float actual, float expected, string message ) => Check( MathF.Abs( actual - expected ) < .001f, message );
var tick = typeof( SpectateController ).GetMethod( "OnUpdate", BindingFlags.Instance | BindingFlags.NonPublic );
void Step( SpectateController camera ) => tick.Invoke( camera, null );

foreach ( var speed in new[] { 10f, 200f, 500f } )
foreach ( var delta in new[] { 1f / 30f, 1f / 60f, 1f / 144f } )
foreach ( var run in new[] { false, true } )
foreach ( var walk in new[] { false, true } )
{
	Input.Run = run;
	Input.Walk = walk;
	Input.AnalogLook = default;
	Input.AnalogMove = new Vector3( 1, 0, 0 );
	Time.Delta = delta;
	var camera = new SpectateController { FlySpeed = speed };
	Step( camera );
	var multiplier = walk ? .25f : run ? 4f : 1f;
	Near( camera.WorldPosition.x, speed * delta * multiplier, "Camera speed must respect frame time, configured base speed, and speed modifiers." );
}

Input.Run = true;
Input.Walk = false;
Input.AnalogMove = new Vector3( 1, 0, 0 );
Input.AnalogLook = new Angles( 20, 40, 0 );
var inactive = new SpectateController { IsLocallyControlled = false };
Step( inactive );
Check( inactive.WorldPosition == default && inactive.EyeAngles == default, "Inactive and remote spectator cameras must not respond to local controls." );

Input.AnalogMove = default;
var looking = new SpectateController { EyeAngles = new Angles( 85, 0, 0 ) };
Step( looking );
Near( looking.EyeAngles.pitch, 90, "Look must preserve the upward pitch limit." );
Near( looking.EyeAngles.yaw, 40, "Look yaw must remain responsive." );
Check( looking.WorldPosition == default, "Holding Sprint without movement must not move the camera." );
Input.AnalogLook = new Angles( -200, 0, 0 );
Step( looking );
Near( looking.EyeAngles.pitch, -90, "Look must preserve the downward pitch limit." );

foreach ( var suppressed in new[] { false, true } )
foreach ( var menuOpen in new[] { false, true } )
{
	if ( !suppressed && !menuOpen ) continue;
	Input.Suppressed = suppressed;
	GameUtils.MenuOpen = menuOpen;
	Input.AnalogMove = new Vector3( 1, 0, 0 );
	Input.AnalogLook = new Angles( 5, 10, 0 );
	var camera = new SpectateController { EyeAngles = new Angles( 20, 30, 0 ), WorldPosition = new Vector3( 10, 20, 30 ) };
	Step( camera );
	Check( camera.EyeAngles == new Angles( 20, 30, 0 ) && camera.WorldPosition == new Vector3( 10, 20, 30 ),
		"Suppressed input and interactive menus must preserve both freecam position and view direction." );
	Input.Suppressed = false;
	GameUtils.MenuOpen = false;
	Step( camera );
	Check( camera.EyeAngles == new Angles( 25, 40, 0 ) && camera.WorldPosition.x > 10,
		"Freecam controls must resume immediately when the UI releases input." );
}

Console.WriteLine( $"PASS: {checks} freecam checks against production SpectateController." );

// Engine seams supply input, time and identity rotation. The production controller applies all movement and guards.
namespace Sandbox
{
	public class Component { protected virtual void OnUpdate() { } }
	public sealed class PropertyAttribute : Attribute;
	public sealed class RequireComponentAttribute : Attribute;
	public class CameraComponent;
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator *( Vector3 a, float scale ) => new( a.x * scale, a.y * scale, a.z * scale );
		public static Vector3 operator *( Vector3 a, Rotation rotation ) => a;
	}
	public readonly record struct Rotation;
	public readonly record struct Angles( float pitch, float yaw, float roll )
	{
		public Angles WithPitch( float value ) => new( value, yaw, roll );
		public Rotation ToRotation() => default;
		public static Angles operator +( Angles a, Angles b ) => new( a.pitch + b.pitch, a.yaw + b.yaw, a.roll + b.roll );
	}
	public static class Numbers { public static float Clamp( this float value, float min, float max ) => Math.Clamp( value, min, max ); }
	public static class Time { public static float Delta { get; set; } }
	public static class Input
	{
		public static bool Run, Walk;
		public static bool Suppressed;
		public static Angles AnalogLook;
		public static Vector3 AnalogMove;
		public static bool Down( string action ) => action switch { "Run" => Run, "Walk" => Walk, _ => false };
	}
}
namespace Facepunch
{
	public static class GameUtils
	{
		public static bool MenuOpen;
		public static bool IsInteractiveMouseUiOpen() => MenuOpen;
	}
	public abstract class Pawn : Component
	{
		public bool IsLocallyControlled { get; set; } = true;
		public Angles EyeAngles { get; set; }
		public Rotation WorldRotation { get; set; }
		public Vector3 WorldPosition { get; set; }
		public virtual string DisplayName => "";
		public virtual CameraComponent Camera => null;
		public virtual void OnPossess() { }
		public virtual void OnDePossess() { }
	}
	public class PawnCameraController { public CameraComponent Camera => null; public void SetActive( bool active ) { } }
}
