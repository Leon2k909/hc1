using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
PlayerFootsteps Walker()
{
	Clock.Now += 10f;
	return new() { Player = new() { WorldPosition = new( 100, 200, 0 ), CharacterController = new() { IsOnGround = true, Velocity = new( 100, 0, 0 ) } } };
}
SceneTraceResult Floor( string name, Vector3 point ) => new() { Hit = true, Surface = new() { Name = name }, HitPosition = point, Normal = Vector3.Up };
void Step( PlayerFootsteps feet, SceneTraceResult floor )
{
	Clock.Now += 1;
	feet.Scene.Trace.Results.Enqueue( floor );
	feet.ProbeFixed();
}

var walker = Walker();
Step( walker, Floor( "metal", new( 100, 206, 0 ) ) );
Check( WorldSounds.LastMaterial == "metal" && WorldSounds.LastLeft, "The first foot must select its own floor material and left-foot sound." );
Check( walker.Scene.Trace.Starts[^1] == new Vector3( 100, 206, 20 ), "Left boot must probe six units left of the body centre." );
Check( Sound.LastPosition == new Vector3( 100, 206, 5 ), "World audio must originate at that foot's contact, not the body centre." );
Step( walker, Floor( "concrete", new( 100, 194, 0 ) ) );
Check( WorldSounds.LastMaterial == "concrete" && !WorldSounds.LastLeft, "The next foot must independently select the other floor material and right-foot sound." );
Check( walker.Scene.Trace.Starts[^1] == new Vector3( 100, 194, 20 ), "Right boot must probe on the opposite side." );
Check( walker.Scene.Trace.Ignored == walker.Player.GameObject && walker.Scene.Trace.Excluded.Contains( "corpse" ), "Floor probes must preserve self/corpse filtering." );

walker.Player.WorldRotation = new( new( -1, 0, 0 ) );
Step( walker, Floor( "wood", new( 94, 200, 0 ) ) );
Check( walker.Scene.Trace.Starts[^1] == new Vector3( 94, 200, 20 ), "Foot spacing must rotate with the body rather than staying in world axes." );

var edge = Walker();
Clock.Now += 1;
edge.Scene.Trace.Results.Enqueue( default );
edge.Scene.Trace.Results.Enqueue( Floor( "wood", edge.Player.WorldPosition ) );
edge.ProbeFixed();
Check( edge.Scene.Trace.Starts.Count == 2 && edge.Scene.Trace.Starts[^1] == new Vector3( 100, 200, 20 ), "An unsupported boot must fall back to the supported centre." );
Check( WorldSounds.LastMaterial == "wood", "Fallback must use the actual centre floor's material." );
var missing = Walker();
var soundsBefore = Sound.Count;
missing.ProbeFixed();
Check( Sound.Count == soundsBefore, "No valid surface must produce no invented footstep." );
Step( missing, Floor( "metal", new( 100, 206, 0 ) ) );
Check( WorldSounds.LastLeft, "A failed floor sample must not consume alternation." );

foreach ( var state in new[] { "dead", "airborne", "stationary", "noclip", "frozen", "mantle", "climb", "slide", "prone", "knocked", "drone" } )
{
	var silent = Walker();
	var player = silent.Player;
	switch ( state )
	{
		case "dead": player.HealthComponent.State = LifeState.Dead; break;
		case "airborne": player.CharacterController.IsOnGround = false; break;
		case "stationary": player.CharacterController.Velocity = default; break;
		case "noclip": player.IsNoclipping = true; break;
		case "frozen": player.IsFrozen = true; break;
		case "mantle": player.IsMantling = true; break;
		case "climb": player.IsPipeClimbing = true; break;
		case "slide": player.IsSliding = true; break;
		case "prone": player.IsProne = true; break;
		case "knocked": player.IsFallKnockedDown = true; break;
		case "drone": player.IsPilotingDrone = true; break;
	}
	var before = Sound.Count;
	Step( silent, Floor( "metal", player.WorldPosition ) );
	Check( Sound.Count == before && silent.Scene.Trace.Starts.Count == 0, $"{state}: existing movement-audio exclusions must remain silent." );
}
foreach ( var crouch in new[] { false, true } )
{
	var quiet = Walker();
	quiet.Player.IsCrouching = crouch;
	quiet.Player.IsSlowWalking = !crouch;
	var before = Sound.Count;
	Step( quiet, Floor( "metal", quiet.Player.WorldPosition ) );
	Check( Sound.Count == before && (float)quiet.TimeSinceStep == 0f, "Quiet crouch/walk must still update timing without playing sounds." );
}
var remote = Walker();
remote.Player.IsLocallyControlled = false;
remote.Player.CharacterController = null;
remote.Player.SyncedIsGrounded = true;
remote.Player.SyncedVelocity = new( 100, 0, 0 );
remote.Player.IsViewer = false;
Step( remote, Floor( "tile", remote.Player.WorldPosition ) );
Check( WorldSounds.LastMaterial == "tile" && Sound.Last.OcclusionEnabled && Sound.Last.SpacialBlend == 1f,
	"Remote steps must use replicated movement and preserve world audio/occlusion." );
var sprint = Walker();
sprint.Player.IsSprinting = true;
Step( sprint, Floor( "metal", sprint.Player.WorldPosition ) );
Check( WorldSounds.LastRunning && sprint.GetStepFrequency() == 0.25f, "Sprint material sampling must retain run sounds and cadence." );
sprint.Player.Components.Ninja = true;
Step( sprint, Floor( "metal", sprint.Player.WorldPosition ) );
Check( Sound.Last.Volume == 0.15f, "Ninja's existing volume reduction must remain applied." );
Console.WriteLine( $"PASS: {checks} production per-foot surface and movement-audio checks." );

// Engine seams only: floor selection, alternating foot placement and movement guards are production code.
namespace Facepunch
{
	public class PropertyAttribute : Attribute;
	public class Component
	{
		public Scene Scene = new();
		public GameObject GameObject = new();
		protected virtual void OnFixedUpdate() { }
		public void ProbeFixed() => OnFixedUpdate();
	}
	public static class Validity { public static bool IsValid( this object value ) => value is not null; }
	public static class Clock { public static float Now; }
	public readonly record struct TimeSince( float Start )
	{
		public static implicit operator TimeSince( float elapsed ) => new( Clock.Now - elapsed );
		public static implicit operator float( TimeSince time ) => Clock.Now - time.Start;
	}
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Up => new( 0, 0, 1 );
		public float LengthSquared => x * x + y * y + z * z;
		public Vector3 WithZ( float value ) => new( x, y, value );
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator *( Vector3 a, float n ) => new( a.x * n, a.y * n, a.z * n );
	}
	public readonly record struct Rotation( Vector3 Left );
	public class GameObject;
	public enum LifeState { Alive, Dead }
	public enum FindMode { EnabledInSelf }
	public class Health : Component { public LifeState State; }
	public class Controller : Component { public bool IsOnGround; public Vector3 Velocity; }
	public class PlayerPawn : Component
	{
		public Vector3 WorldPosition, SyncedVelocity;
		public Rotation WorldRotation = new( new( 0, 1, 0 ) );
		public Health HealthComponent = new();
		public Controller CharacterController;
		public bool IsLocallyControlled = true, IsViewer = true, SyncedIsGrounded;
		public bool IsSprinting, IsCrouching, IsSlowWalking, IsNoclipping, IsFrozen, IsMantling,
			IsPipeClimbing, IsSliding, IsProne, IsFallKnockedDown, IsPilotingDrone;
		public Components Components = new();
	}
	public class Components
	{
		public bool Ninja;
		public bool TryGet<T>( out T value, FindMode mode ) where T : class { value = new PlayerPerks { Ninja = Ninja } as T; return true; }
	}
	public class PlayerPerks { public bool Ninja; public bool HasPerk( string id ) => Ninja; }
	public class Scene { public TraceStub Trace = new(); }
	public class TraceStub
	{
		public Queue<SceneTraceResult> Results = new();
		public List<Vector3> Starts = new();
		public GameObject Ignored;
		public string[] Excluded;
		public TraceStub Ray( Vector3 start, Vector3 end ) { Starts.Add( start ); return this; }
		public TraceStub IgnoreGameObjectHierarchy( GameObject item ) { Ignored = item; return this; }
		public TraceStub WithoutTags( params string[] tags ) { Excluded = tags; return this; }
		public SceneTraceResult Run() => Results.TryDequeue( out var result ) ? result : default;
	}
	public record struct SceneTraceResult { public bool Hit; public Surface Surface; public Vector3 HitPosition, Normal; }
	public class Surface { public string Name; }
	public class SoundEvent;
	public class SoundHandle { public float Volume = 1f, SpacialBlend = 1f; public bool OcclusionEnabled = true; }
	public static class Sound
	{
		public static int Count;
		public static Vector3 LastPosition;
		public static SoundHandle Last;
		public static SoundHandle Play( SoundEvent sound, Vector3 position ) { Count++; LastPosition = position; return Last = new(); }
	}
	public static class WorldSounds
	{
		public static string LastMaterial;
		public static bool LastRunning, LastLeft;
		public static Surface SurfaceAt( SceneTraceResult result ) => result.Surface;
		public static SoundEvent Footstep( Surface surface, bool running, bool left ) { LastMaterial = surface.Name; LastRunning = running; LastLeft = left; return new(); }
	}
}
