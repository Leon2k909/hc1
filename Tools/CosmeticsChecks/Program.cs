using Facepunch;
using System.Text.Json;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
foreach ( var url in new[] { "https://example.com/art.png", "https://example.com/art.JPG?v=2", " https://example.com/art.webp " } )
	Check( CosmeticCatalog.TryImageUrl( url, out var result ) && result.StartsWith( "https://" ), "Direct HTTPS image URLs must be supported." );
foreach ( var url in new[] { null, "", "http://example.com/art.png", "file:///c:/image.png", "javascript:alert(1)", "data:image/png,x",
	"https://example.com/page", "https://example.com/a.mp4", "https://user:password@example.com/art.png", "https://example.com/art.png#fragment", new string( 'x', 2049 ) } )
	Check( !CosmeticCatalog.TryImageUrl( url, out _ ), "Invalid or unsupported personal image URLs must be rejected." );

LoadingScreen.Media = "engine-default";
CosmeticPreferences.SelectLoadingScreen( "orion" );
Check( LoadingScreen.Media == "ui/maps/orion.png", "Selecting artwork must update the real loading-screen media seam." );
CosmeticPreferences.SelectLoadingScreen( "collider" );
CosmeticPreferences.SelectLoadingScreen( "default" );
Check( LoadingScreen.Media == "engine-default", "Restoring default after several choices must restore the original game media." );
Check( CosmeticPreferences.SelectCustomImage( "https://example.com/personal.png" ) && CosmeticPreferences.LoadingId == "custom",
	"A personal loading image must be selectable and saved." );
Check( CosmeticPreferences.LoadingImage == "https://example.com/personal.png", "The selected personal image must be restored from preferences." );
var version = CosmeticPreferences.Version;
Check( !CosmeticPreferences.SelectCustomImage( "http://example.com/no.png" ) && CosmeticPreferences.Version == version,
	"A rejected URL must not change the saved selection." );
CosmeticPreferences.SelectSpray( "sentinel" );
CosmeticPreferences.SelectSpray( "https://example.com/personal.png" );
Check( CosmeticPreferences.SprayId == "sentinel", "Personal image URLs must never enter the spray catalogue." );
Game.Cookies.Set( "hc1.cosmetics.spray.v1", "unknown" );
Check( CosmeticPreferences.SprayId == "precision", "Unknown saved spray IDs must fall back to a shipped spray." );
Game.Cookies.Set( "hc1.cosmetics.loading-image.v1", "bad" );
Check( CosmeticPreferences.LoadingId == "default", "Corrupt personal-image preferences must fall back to the default." );
CosmeticPreferences.ApplyLoadingScreen();
LoadingScreen.Media = "next-map-default";
CosmeticPreferences.SelectLoadingScreen( "orion" );
CosmeticPreferences.SelectLoadingScreen( "default" );
Check( LoadingScreen.Media == "next-map-default", "A later map's loading media must replace the earlier default baseline." );

Client Fixture()
{
	Clock.Now += 20;
	Game.ActiveScene = new();
	var client = new Client { Connection = new(), IsLocalPlayer = true, Scene = Game.ActiveScene };
	client.PlayerPawn = new() { Scene = client.Scene, SprayEyePosition = new( 0, 0, 48 ) };
	client.Scene.Trace.Result = new() { Hit = true, HitPosition = new( 40, 0, 48 ), Normal = new( -1, 0, 0 ), Surface = new() { ResourceName = "concrete" } };
	Rpc.Caller = client.Connection;
	return client;
}
int Marks( Client client ) => client.Scene.GetAllComponents<SprayMark>().Count();
var direction = new Vector3( 1, 0, 0 );
var valid = Fixture();
valid.RequestSpray( "precision", direction );
Check( Marks( valid ) == 1, "A valid owned request must place a networked spray." );
Check( valid.Scene.Trace.From == valid.PlayerPawn.SprayEyePosition && valid.Scene.Trace.To == new Vector3( 96, 0, 48 ),
	"Placement must retrace from the host eye to exactly the allowed reach." );
Check( valid.Scene.GetAllComponents<SprayMark>().Single().GameObject.Networked, "Accepted sprays must be network spawned for observers and late joiners." );
Clock.Now += 1;
valid.RequestSpray( "fieldcraft", direction );
Check( Marks( valid ) == 1 && valid.Scene.GetAllComponents<SprayMark>().Single().SprayId == "precision", "Cooldown must prevent replacement." );
Clock.Now += 10;
valid.RequestSpray( "fieldcraft", direction );
Check( Marks( valid ) == 1 && valid.Scene.GetAllComponents<SprayMark>().Single().SprayId == "fieldcraft", "A fresh spray must replace that player's previous one." );

foreach ( var block in new[] { "other-caller", "dead", "frozen", "noclip", "drone", "mantle", "climb", "bad-id", "bad-direction", "rearward", "miss", "solid", "water", "sky", "moving-prop", "body", "wrong-scene" } )
{
	var client = Fixture();
	var id = "precision";
	var aim = direction;
	switch ( block )
	{
		case "other-caller": Rpc.Caller = new(); break;
		case "dead": client.PlayerPawn.HealthComponent.State = LifeState.Dead; break;
		case "frozen": client.PlayerPawn.IsFrozen = true; break;
		case "noclip": client.PlayerPawn.IsNoclipping = true; break;
		case "drone": client.PlayerPawn.IsPilotingDrone = true; break;
		case "mantle": client.PlayerPawn.IsMantling = true; break;
		case "climb": client.PlayerPawn.IsPipeClimbing = true; break;
		case "bad-id": id = "https://example.com/spray.png"; break;
		case "bad-direction": aim = new( float.NaN, 0, 0 ); break;
		case "rearward": aim = new( -1, 0, 0 ); break;
		case "miss": client.Scene.Trace.Result.Hit = false; break;
		case "solid": client.Scene.Trace.Result.StartedSolid = true; break;
		case "water": client.Scene.Trace.Result.Surface.ResourceName = "water"; break;
		case "sky": client.Scene.Trace.Result.Surface.ResourceName = "sky"; break;
		case "moving-prop": client.Scene.Trace.Result.GameObject = new(); client.Scene.Trace.Result.GameObject.Components.Create<Rigidbody>(); break;
		case "body": client.Scene.Trace.Result.GameObject = new(); client.Scene.Trace.Result.GameObject.Components.Create<HealthComponent>(); break;
		case "wrong-scene": client.PlayerPawn.Scene = new(); break;
	}
	client.RequestSpray( id, aim );
	Check( Marks( client ) == 0, $"{block}: host must reject spray placement." );
}
var capped = Fixture();
for ( var i = 0; i < SprayRules.SceneLimit; i++ ) new GameObject().Components.Create<SprayMark>();
capped.RequestSpray( "precision", direction );
Check( Marks( capped ) == SprayRules.SceneLimit, "The scene cap must prevent excess spray objects." );
var floor = Fixture();
floor.Scene.Trace.Result.Normal = new( 0, 0, 1 );
floor.RequestSpray( "precision", direction );
Check( Marks( floor ) == 1 && floor.Scene.GetAllComponents<SprayMark>().Single().GameObject.WorldRotation.Up.Dot( new( 0, 0, 1 ) ) == 0f,
	"Floor sprays must use a nonparallel orientation axis." );

var root = args[0];
foreach ( var art in CosmeticCatalog.Sprays.Concat( CosmeticCatalog.LoadingScreens ).Where( x => x.Image.Length > 0 ) )
	Check( File.Exists( Path.Combine( root, "Assets", art.Image ) ), $"Catalogue image must exist: {art.Image}" );
using var config = JsonDocument.Parse( File.ReadAllText( Path.Combine( root, "ProjectSettings/Input.config" ) ) );
var action = config.RootElement.GetProperty( "Actions" ).EnumerateArray().Single( x => x.GetProperty( "Name" ).GetString() == "Spray" );
Check( action.GetProperty( "KeyboardCode" ).GetString() == "None" && action.GetProperty( "GamepadCode" ).GetString() == "None", "New spray controls must not steal existing bindings." );
Console.WriteLine( $"PASS: {checks} production cosmetics preference, host-placement and asset checks." );

namespace Facepunch
{
	public static class Clock { public static float Now; }
	public readonly record struct TimeSince( float Start )
	{
		public static implicit operator TimeSince( float elapsed ) => new( Clock.Now - elapsed );
		public static implicit operator float( TimeSince time ) => Clock.Now - time.Start;
	}
	public readonly record struct RealTimeSince( float Start )
	{
		public static implicit operator RealTimeSince( float elapsed ) => new( Clock.Now - elapsed );
		public static implicit operator float( RealTimeSince time ) => Clock.Now - time.Start;
	}
	public class Component { public GameObject GameObject; }
	public static class Validity
	{
		public static bool IsValid( this Component item ) => item is not null;
		public static bool IsValid( this GameObject item ) => item is not null && !item.Destroyed;
	}
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Up => new( 0, 0, 1 );
		public float Length => MathF.Sqrt( Dot( this ) );
		public Vector3 Normal => this * (1f / Length);
		public float Dot( Vector3 other ) => x * other.x + y * other.y + z * other.z;
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator -( Vector3 a ) => new( -a.x, -a.y, -a.z );
		public static Vector3 operator *( Vector3 a, float scale ) => new( a.x * scale, a.y * scale, a.z * scale );
	}
	public readonly record struct Rotation( Vector3 Forward, Vector3 Up ) { public static Rotation LookAt( Vector3 f, Vector3 u ) => new( f, u ); }
	public readonly record struct Angles { public Vector3 Forward => new( 1, 0, 0 ); public Angles WithPitch( float pitch ) => this; }
	public enum LifeState { Alive, Dead }
	public enum GameObjectFlags { NotSaved }
	public class Connection;
	public static class Networking { public static bool IsHost = true; }
	public static class Application { public static bool IsDedicatedServer; }
	public static class LoadingScreen { public static string Media; }
	public static class Game
	{
		public static CookieStore Cookies = new();
		public static Scene ActiveScene;
		public class CookieStore
		{
			private readonly Dictionary<string, object> values = new();
			public T Get<T>( string key, T fallback ) => values.TryGetValue( key, out var value ) ? (T)value : fallback;
			public void Set<T>( string key, T value ) => values[key] = value;
		}
	}
	public static class Rpc
	{
		public static Connection Caller;
		public class HostAttribute : Attribute;
		public class OwnerAttribute : Attribute;
	}
	public class GameObject
	{
		public bool Destroyed, Networked;
		public GameObjectFlags Flags;
		public Vector3 WorldPosition;
		public Rotation WorldRotation;
		public readonly Scene Scene;
		public Components Components;
		public Tags Tags = new();
		public GameObject( bool enabled = true, string name = "" ) { Scene = Game.ActiveScene; Scene?.Objects.Add( this ); Components = new( this ); }
		public T GetComponentInParent<T>() where T : Component => Components.Items.OfType<T>().FirstOrDefault();
		public void NetworkSpawn() => Networked = true;
		public void Destroy() => Destroyed = true;
	}
	public class Components( GameObject owner )
	{
		public List<Component> Items = new();
		public T Create<T>() where T : Component, new() { var item = new T { GameObject = owner }; Items.Add( item ); return item; }
	}
	public class Tags { public bool Has( string tag ) => false; }
	public class Scene
	{
		public List<GameObject> Objects = new();
		public TraceStub Trace = new();
		public IEnumerable<T> GetAllComponents<T>() where T : Component => Objects.Where( x => !x.Destroyed ).SelectMany( x => x.Components.Items ).OfType<T>();
	}
	public class TraceStub
	{
		public TraceResult Result;
		public Vector3 From, To;
		public TraceStub Ray( Vector3 from, Vector3 to ) { From = from; To = to; return this; }
		public TraceStub IgnoreGameObjectHierarchy( GameObject obj ) => this;
		public TraceStub WithoutTags( params string[] tags ) => this;
		public TraceResult Run() => Result;
	}
	public struct TraceResult { public bool Hit, StartedSolid; public Surface Surface; public Vector3 HitPosition, Normal; public GameObject GameObject; }
	public class Surface { public string ResourceName; }
	public class PlayerPawn : Component
	{
		public Scene Scene;
		public Vector3 SprayEyePosition;
		public Angles EyeAngles;
		public HealthComponent HealthComponent = new();
		public bool IsFrozen, IsNoclipping, IsPilotingDrone, IsMantling, IsPipeClimbing;
	}
	public class HealthComponent : Component { public LifeState State = LifeState.Alive; }
	public class Rigidbody : Component;
	public class ZombieAI : Component;
	public class DestroyBetweenRounds : Component;
	public class SprayMark : Component { public string SprayId; }
	public partial class Client
	{
		public Connection Connection;
		public bool IsBot, IsLocalPlayer;
		public PlayerPawn PlayerPawn;
		public Scene Scene;
	}
}
namespace Facepunch.UI
{
	public class Toast { public static Toast Instance; public void Show( string text, float duration ) { } }
}
