using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
SceneTraceResult Entry( float at, string material, bool body = false ) => new()
{
	Hit = true, Distance = at, EndPosition = new( at, 0, 0 ), Direction = new( 1, 0, 0 ),
	Shape = new(), Surface = new() { ResourceName = material }, Body = body
};
void Exit( Scene scene, SceneTraceResult entry, float thickness, object shape = null ) => scene.Exits.Enqueue(
	[new SceneTraceResult { Hit = true, Shape = shape ?? entry.Shape,
		EndPosition = entry.EndPosition + new Vector3( thickness, 0, 0 ), Normal = new( 1, 0, 0 ) }] );
(SceneTraceResult[] Hits, float[] Scales) Resolve( Scene scene, SceneTraceResult[] hits, float budget = 8f )
{
	var scales = new List<float>();
	var resolved = Shootable.ResolvePenetrationWithDamage( scene, hits, budget, scales.Add ).ToArray();
	return (resolved, scales.ToArray());
}

var target = Entry( 100, "flesh", true );
var wood = Entry( 10, "wood" );
var scene = new Scene();
var open = Resolve( scene, [target] );
Check( open.Scales.SequenceEqual( new[] { 1f } ), "An open shot must retain its full damage." );
Exit( scene, wood, 1f );
var crossed = Resolve( scene, [target, wood] );
Check( crossed.Hits.Length == 2 && crossed.Hits[0] == wood, "Resolver must sort impacts nearest-first." );
Check( crossed.Scales[0] == 1f && crossed.Scales[1] == 0.875f,
	"Entry gets incoming damage; the target gets damage only after the round has crossed the wood." );

var paper = Entry( 30, "paper" );
Exit( scene, wood, 1f );
Exit( scene, paper, 1f );
var layers = Resolve( scene, [target, paper, wood] );
Check( MathF.Abs( layers.Scales[^1] - 0.875f * 0.9f ) < 0.00001f,
	"Loss through multiple materials must accumulate multiplicatively." );
var fresh = Resolve( scene, [target] );
Check( fresh.Scales[0] == 1f, "A fresh ray/pellet must never inherit another ray's penetration loss." );

foreach ( var material in new[] { "wood", "plastic", "metal.sheet", "glass", "glass.pane", "fabric", "paper", "cardboard" } )
{
	var loss = PenetrationDamageRules.LossPerUnit( material );
	var thin = PenetrationDamageRules.RetainedFraction( loss, 0.05f );
	var thick = PenetrationDamageRules.RetainedFraction( loss, 0.1f );
	Check( thin < 1f && thick < thin && thick >= 0f, $"{material}: thicker material must retain less damage." );
	var panel = Entry( 10, material );
	Exit( scene, panel, 0.05f );
	var result = Resolve( scene, [panel, target] );
	Check( result.Hits.Length == 2 && MathF.Abs( result.Scales[^1] - thin ) < 0.00001f,
		$"{material}: the actual penetration iterator must deliver reduced damage after a valid exit." );
}
var custom = Entry( 10, "custom_panel" );
custom.Surface.Base = new() { ResourceName = "wood" };
Exit( scene, custom, 2f );
Check( Resolve( scene, [custom, target] ).Scales[^1] == 0.75f, "Derived surfaces must inherit the base material's loss." );

foreach ( var blocking in new[] { "default", "concrete", "metal" } )
	Check( Resolve( scene, [Entry( 10, blocking ), target] ).Hits.Length == 1, "Solid/unknown cover must still stop the round." );
Check( Resolve( scene, [wood, target] ).Hits.Length == 1, "A missing exit must not allow a reduced-damage shot through." );
Exit( scene, wood, 5f );
Check( Resolve( scene, [wood, target] ).Hits.Length == 1, "Over-thickness cover must still stop the round." );
Exit( scene, wood, 1f, new object() );
Check( Resolve( scene, [wood, target] ).Hits.Length == 1, "An exit on another shape must never count." );
Check( Resolve( scene, [wood, target], 0f ).Hits.Length == 1, "An exhausted thickness budget must stop at the first impact." );
var secondBody = Entry( 120, "flesh", true );
Check( Resolve( scene, [target, secondBody] ).Hits.Length == 1, "Rounds must still stop at the first body." );
Exit( scene, wood, 1f );
Check( Shootable.ResolvePenetration( scene, [wood, target], 8f ).Count() == 2,
	"The existing three-argument penetration API must retain its hit sequence." );
foreach ( var invalid in new[] { float.NaN, float.PositiveInfinity, -1f, 0f } )
	Check( PenetrationDamageRules.RetainedFraction( invalid, 1f ) == 1f
		&& PenetrationDamageRules.RetainedFraction( 0.1f, invalid ) == 1f, "Invalid loss inputs must not corrupt shot damage." );
Check( PenetrationDamageRules.RetainedFraction( float.MaxValue, float.MaxValue ) == 0f, "Extreme losses must clamp at zero damage." );
Console.WriteLine( $"PASS: {checks} production penetration and damage-loss checks." );

// Deterministic engine seams; the material resolver and damage math are linked from production.
namespace Facepunch
{
	public static class MathExtensions { public static float Clamp( this float value, float min, float max ) => Math.Clamp( value, min, max ); }
	public readonly record struct Vector3( float x, float y, float z )
	{
		public Vector3 Normal { get { var length = MathF.Sqrt( Dot( this ) ); return length > 0 ? this * (1f / length) : default; } }
		public float Dot( Vector3 other ) => x * other.x + y * other.y + z * other.z;
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator -( Vector3 a, Vector3 b ) => new( a.x - b.x, a.y - b.y, a.z - b.z );
		public static Vector3 operator *( Vector3 a, float n ) => new( a.x * n, a.y * n, a.z * n );
	}
	public class Surface
	{
		public string ResourceName;
		public Surface Base;
		public Surface GetBaseSurface() => Base;
	}
	public record struct SceneTraceResult
	{
		public bool Hit, StartedSolid, Body;
		public float Distance;
		public Vector3 Direction, EndPosition, Normal;
		public object Shape;
		public Surface Surface;
	}
	public class Scene
	{
		public Queue<SceneTraceResult[]> Exits = new();
		public Scene Trace => this;
		public Scene Ray( Vector3 from, Vector3 to ) => this;
		public Scene WithoutTags( params string[] tags ) => this;
		public SceneTraceResult[] RunAll() => Exits.TryDequeue( out var exits ) ? exits : [];
	}
	public partial class Shootable { private static bool IsBody( SceneTraceResult result ) => result.Body; }
}
