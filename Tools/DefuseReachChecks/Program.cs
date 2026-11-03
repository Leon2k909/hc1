global using Sandbox;
using Facepunch;
using System.Reflection;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var update = typeof( TimedExplosive ).GetMethod( "OnUpdate", BindingFlags.Instance | BindingFlags.NonPublic );
PlayerPawn Defender() => new() { Team = Team.CounterTerrorist, WorldPosition = new Vector3( 20, 0, 0 ), IsUsing = true };
void Tick( TimedExplosive bomb ) => update.Invoke( bomb, null );

Clock.Now = 0;
var blocked = new TimedExplosive();
var player = Defender();
blocked.Scene.Trace.Blocked = true;
Check( !blocked.CanUse( player ).CanUse, "A defender behind solid cover must not be allowed to start defusing." );
blocked.StartDefusing( player );
Check( blocked.DefusingPlayer is null && !player.IsFrozen, "A blocked start must not freeze the player or start a defuse." );

var interrupted = new TimedExplosive();
player = Defender();
interrupted.StartDefusing( player );
Check( interrupted.DefusingPlayer == player && player.IsFrozen, "A reachable defender must still be able to start." );
Check( interrupted.Scene.Trace.LastStart == player.EyePosition && interrupted.Scene.Trace.LastEnd == interrupted.WorldPosition + Vector3.Up * 4,
	"Access must be checked from the defender's eyes to a point above the bomb's ground origin." );
Check( interrupted.Scene.Trace.Ignored.Contains( player.GameObject ) && interrupted.Scene.Trace.Ignored.Contains( interrupted.GameObject ),
	"The defender and bomb must not block their own access trace." );
Check( interrupted.Scene.Trace.Excluded.Contains( "trigger" ) && interrupted.Scene.Trace.Excluded.Contains( "ragdoll" ),
	"Non-solid gameplay volumes and corpses must not prevent access." );
interrupted.Scene.Trace.Blocked = true;
Clock.Now = 11;
Tick( interrupted );
Check( !interrupted.IsDefused && interrupted.DefusingPlayer is null && !player.IsFrozen,
	"A door closing before completion must cancel the defuse and release the defender." );

foreach ( var kit in new[] { false, true } )
{
	Clock.Now = 0;
	var bomb = new TimedExplosive();
	var defender = Defender();
	defender.Inventory.HasDefuseKit = kit;
	bomb.StartDefusing( defender );
	Clock.Now = (kit ? bomb.FastDefuseTime : bomb.BaseDefuseTime) - .1f;
	Tick( bomb );
	Check( !bomb.IsDefused && bomb.DefusingPlayer == defender, "A clear defuse must not finish early." );
	Clock.Now += .2f;
	Tick( bomb );
	Check( bomb.IsDefused && bomb.DefusingPlayer is null && !defender.IsFrozen,
		"Clear defuses must still complete at their original normal or kit-assisted duration." );
}

foreach ( var invalid in new[] { "team", "dead", "range", "no health" } )
{
	var bomb = new TimedExplosive();
	var defender = Defender();
	if ( invalid == "team" ) defender.Team = Team.Terrorist;
	if ( invalid == "dead" ) defender.HealthComponent.State = LifeState.Dead;
	if ( invalid == "range" ) defender.WorldPosition = new Vector3( 1000, 0, 0 );
	if ( invalid == "no health" ) defender.HealthComponent = null;
	Check( !bomb.CanUse( defender ).CanUse && bomb.Scene.Trace.Runs == 0, $"{invalid}: invalid defenders must be rejected before tracing." );
}
Check( !new TimedExplosive().CanUse( null ).CanUse, "A missing defender must be rejected safely." );

Console.WriteLine( $"PASS: {checks} defuse access checks against production TimedExplosive." );

// Engine seams supply visibility, time and event recording. Production code owns defuse eligibility and completion.
namespace Sandbox
{
	public static class Clock { public static float Now; }
	public readonly record struct TimeSince( float Started )
	{
		public static implicit operator TimeSince( float elapsed ) => new( Clock.Now - elapsed );
		public static implicit operator float( TimeSince time ) => Clock.Now - time.Started;
	}
	public interface IValid { bool IsValid { get; } }
	public class Component : IValid
	{
		public GameObject GameObject { get; } = new();
		public Scene Scene { get; } = new();
		public bool IsValid => !GameObject.Destroyed;
		public Vector3 WorldPosition { get => GameObject.WorldPosition; set => GameObject.WorldPosition = value; }
		public T GetComponent<T>() where T : class => this as T;
		protected virtual void OnStart() { }
		protected virtual void OnUpdate() { }
		protected virtual void OnDisabled() { }
		protected virtual void OnDestroy() { }
	}
	public static class Validity { public static bool IsValid( this IValid value ) => value?.IsValid == true; }
	public class GameObject : IValid
	{
		public bool Destroyed;
		public bool IsValid => !Destroyed;
		public Vector3 WorldPosition;
		public GameObject Clone( Vector3 position, Rotation rotation = default ) => new();
		public T GetComponent<T>() where T : class => null;
		public void NetworkSpawn() { }
		public void Destroy() => Destroyed = true;
	}
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Up => new( 0, 0, 1 );
		public float Length => MathF.Sqrt( x * x + y * y + z * z );
		public Vector3 Normal => Length > 0 ? this * (1 / Length) : default;
		public float Distance( Vector3 other ) => (this - other).Length;
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator -( Vector3 a, Vector3 b ) => new( a.x - b.x, a.y - b.y, a.z - b.z );
		public static Vector3 operator *( Vector3 a, float scale ) => new( a.x * scale, a.y * scale, a.z * scale );
	}
	public readonly record struct Rotation { public static Rotation FromYaw( float yaw ) => default; }
	public class Scene
	{
		public TraceStub Trace { get; } = new();
		public List<object> Events { get; } = new();
		public void Dispatch( object message ) => Events.Add( message );
		public IEnumerable<T> GetAllComponents<T>() => [];
	}
	public class TraceStub
	{
		public bool Blocked;
		public int Runs;
		public Vector3 LastStart, LastEnd;
		public List<GameObject> Ignored { get; } = new();
		public string[] Excluded = [];
		public TraceStub Ray( Vector3 start, Vector3 end ) { LastStart = start; LastEnd = end; Ignored.Clear(); return this; }
		public TraceStub IgnoreGameObjectHierarchy( GameObject obj ) { Ignored.Add( obj ); return this; }
		public TraceStub WithoutTags( params string[] tags ) { Excluded = tags; return this; }
		public TraceResult Run() { Runs++; return new( Blocked ); }
	}
	public readonly record struct TraceResult( bool Hit );
	public sealed class PropertyAttribute : Attribute;
	public sealed class RequireComponentAttribute : Attribute;
	public sealed class CategoryAttribute( string category ) : Attribute { public string Category => category; }
	public enum SyncFlags { FromHost }
	public sealed class SyncAttribute( SyncFlags flags ) : Attribute { public SyncFlags Flags => flags; }
	public enum NetFlags { HostOnly }
	public static class Rpc { public sealed class BroadcastAttribute( NetFlags flags ) : Attribute { public NetFlags Flags => flags; } }
	public static class Networking { public static bool IsHost => true; }
	public class SoundEvent;
	public static class Sound { public static void Play( SoundEvent sound, Vector3 position ) { } }
	public class Curve( params Curve.Frame[] frames )
	{
		public Frame[] Frames => frames;
		public readonly record struct Frame( float Time, float Value );
		public float Evaluate( float progress ) => 1;
	}
	public class LineRenderer : Component { public List<GameObject> Points { get; } = [null, null]; }
	public static class Log { public static void Warning( string message ) { } }
}
namespace Sandbox.Events { }
namespace Facepunch
{
	public enum Team { Unassigned, Terrorist, CounterTerrorist }
	public enum LifeState { Alive, Dead }
	public enum HitboxTags { UpperBody }
	public enum DamageFlags { Explosion }
	public record DamageInfo( Component Attacker, float Damage, Component Inflictor, Vector3 Position, Vector3 Force, HitboxTags Hitbox, DamageFlags Flags );
	public class HealthComponent : Component { public LifeState State { get; set; } = LifeState.Alive; public void TakeDamage( DamageInfo info ) { } }
	public class Pawn : Component { public Team Team { get; set; } }
	public class PlayerPawn : Pawn
	{
		public HealthComponent HealthComponent { get; set; } = new();
		public float UseDistance => 72;
		public bool IsFrozen, IsUsing;
		public Vector3 EyePosition => WorldPosition + Vector3.Up * 64;
		public GameObject CameraGameObject { get; } = new();
		public Inventory Inventory { get; } = new();
	}
	public class Inventory { public bool HasDefuseKit; }
	public class Spottable : Component { public bool IsSpotted; }
	public class BombSite : Component { public float GetExplosionDamage( float distance ) => 0; }
	public class Zone : Component { public static IEnumerable<Zone> GetAt( Vector3 position ) => []; }
	public interface IMinimapElement { Vector3 WorldPosition { get; } bool IsVisible( Pawn viewer ); }
	public interface IMinimapIcon : IMinimapElement { string IconPath { get; } }
	public interface IDescription { string DisplayName { get; } string Icon { get; } }
	public class UseResult { public bool CanUse; public static implicit operator UseResult( bool allowed ) => new() { CanUse = allowed }; }
	public interface IUse { UseResult CanUse( PlayerPawn player ); void OnUse( PlayerPawn player ); }
	public record BombDefuseStartEvent( PlayerPawn Player, GameObject Bomb, BombSite Site );
	public record BombDefusedEvent( PlayerPawn Player, GameObject Bomb, BombSite Site );
	public record BombDetonatedEvent( GameObject Bomb, BombSite Site );
	public class FreezePlayers { public bool Active; }
	public class GameMode { public static GameMode Instance => null; public T Get<T>() where T : class => null; }
	public static class RadioSounds { public static void Play( Team team, string category, string message ) { } }
	public class DemolitionBlast { public float EquivalentKg => 0; public static void BreakWindows( Scene scene, Vector3 position, float kg, GameObject ignored ) { } }
}
