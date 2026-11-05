using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	checks++;
	if ( !condition ) throw new Exception( message );
}
foreach ( var count in new[] { 1, 2, 8 } )
foreach ( var useHealth in new[] { true, false } )
{
	var scene = Game.ActiveScene = new Scene();
	var root = new GameObject();
	DamageTarget target = useHealth ? root.Add( new HealthComponent() ) : root.Add( new Prop() );
	for ( var i = 0; i < count; i++ )
		scene.Objects.Add( new GameObject { Root = root, WorldPosition = new( 10, 0, 0 ) } );
	Explosion.AtPoint( default, 100, 50 );
	Check( target.Hits == 1, "One hit per target regardless of collider count" );
	Check( target.TotalDamage == 50, "Collider count cannot multiply damage" );
	Explosion.AtPoint( default, 100, 50 );
	Check( target.Hits == 2, "A later explosion can hit the same target" );
}
foreach ( var allBlocked in new[] { true, false } )
{
	var scene = Game.ActiveScene = new Scene();
	var root = new GameObject();
	var target = root.Add( new HealthComponent() );
	var wall = new GameObject();
	foreach ( var x in new[] { 10f, 20f, 30f } )
		scene.Objects.Add( new GameObject { Root = root, WorldPosition = new( x, 0, 0 ) } );
	scene.Trace.Result = end => new() { Hit = allBlocked || end.X == 10, GameObject = wall };
	Explosion.AtPoint( default, 100, 50 );
	Check( target.Hits == (allBlocked ? 0 : 1), "Blocked first collider cannot hide another exposed collider; full cover still protects" );
}
{
	var scene = Game.ActiveScene = new Scene();
	var targets = new List<HealthComponent>();
	for ( var i = 0; i < 3; i++ )
	{
		var root = new GameObject();
		targets.Add( root.Add( new HealthComponent() ) );
		for ( var c = 0; c < 4; c++ )
			scene.Objects.Add( new GameObject { Root = root, WorldPosition = new( 10, 0, 0 ) } );
	}
	Explosion.AtPoint( default, 100, 50 );
	Check( targets.All( t => t.Hits == 1 ), "Different bodies each receive one hit" );
}
Console.WriteLine( $"Passed {checks} production explosion target checks." );

// Minimal engine seams; production Explosion.AtPoint performs all iteration and damage dispatch.
namespace Facepunch
{
	public record struct Vector3( float X, float Y, float Z )
	{
		public static Vector3 Up => new( 0, 0, 1 );
		public float Length => MathF.Sqrt( X*X + Y*Y + Z*Z );
		public Vector3 Normal => Length > 0 ? this * (1 / Length) : default;
		public float Distance( Vector3 other ) => (this - other).Length;
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.X+b.X, a.Y+b.Y, a.Z+b.Z );
		public static Vector3 operator -( Vector3 a, Vector3 b ) => new( a.X-b.X, a.Y-b.Y, a.Z-b.Z );
		public static Vector3 operator *( Vector3 a, float n ) => new( a.X*n, a.Y*n, a.Z*n );
	}
	public record Sphere( Vector3 Centre, float Radius );
	public struct Curve
	{
		public record Frame( float X, float Y );
		public Curve( params Frame[] frames ) { }
		public FrameList Frames => new();
		public float Evaluate( float fraction ) => 1;
		public struct FrameList { public bool IsEmpty => false; }
	}
	public static class Validity { public static bool IsValid( this object value ) => value is not null; }
	public class Component
	{
		public GameObject GameObject { get; set; }
		public Vector3 WorldPosition => GameObject.WorldPosition;
		public interface IDamageable { void OnDamage( DamageInfo info ); }
	}
	public class GameObject
	{
		private GameObject root;
		private readonly List<Component> components = new();
		public GameObject Root { get => root ?? this; set => root = value; }
		public Vector3 WorldPosition { get; set; }
		public T Add<T>( T component ) where T : Component { component.GameObject = this; components.Add( component ); return component; }
		public T GetComponentInChildren<T>() where T : class => components.OfType<T>().FirstOrDefault();
		public T GetComponentInParent<T>() where T : class => Root.GetComponentInChildren<T>();
		public IEnumerable<T> GetComponents<T>() => components.OfType<T>();
		public bool IsDescendant( GameObject obj ) => obj.Root == Root;
	}
	public class Scene
	{
		public List<GameObject> Objects { get; } = new();
		public SceneTrace Trace { get; } = new();
		public IEnumerable<GameObject> FindInPhysics( Sphere sphere ) => Objects;
	}
	public static class Game { public static Scene ActiveScene { get; set; } }
	public class SceneTrace
	{
		private Vector3 end;
		public Func<Vector3, SceneTraceResult> Result { get; set; } = _ => default;
		public SceneTrace WithoutTags( params string[] tags ) => this;
		public SceneTrace IgnoreGameObjectHierarchy( GameObject root ) => this;
		public SceneTrace Ray( Vector3 start, Vector3 end ) { this.end = end; return this; }
		public SceneTraceResult Run() => Result( end );
	}
	public struct SceneTraceResult { public bool Hit; public GameObject GameObject; }
	public enum DamageFlags { Explosion }
	public enum BlastLimb { None }
	public record DamageInfo( Component Attacker, float Damage, Component Inflictor, Vector3 Position, Vector3 Force, DamageFlags Flags )
	{
		public BlastLimb SeveredLimbs { get; init; }
	}
	public class DamageTarget : Component
	{
		public int Hits; public float TotalDamage;
		public void TakeDamage( DamageInfo info ) { Hits++; TotalDamage += info.Damage; }
	}
	public class HealthComponent : DamageTarget;
	public class Prop : DamageTarget { public void OnDamage( DamageInfo info ) => TakeDamage( info ); }
	public class LpgCanister : DamageTarget;
	public static class BreakableGlass
	{
		public const string Tag = "glass";
		public static void BreakInBlast( List<GameObject> objects, Vector3 point, SceneTrace trace ) { }
	}
	public static class BlastDismemberment { public static BlastLimb Select( HealthComponent health, Vector3 point, SceneTrace trace ) => BlastLimb.None; }
}
namespace Tec { public static class Utils { public static DamageInfo CreateDamageInfo( DamageInfo info ) => info; } }
