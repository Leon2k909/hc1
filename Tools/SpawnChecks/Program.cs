global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}

SpawnPointInfo Spawn( float x ) => new( new Transform( new Vector3( x, 0, 0 ) ), Array.Empty<string>() );
var owner = new Client { Team = Team.Unassigned, DisplayName = "Respawning player" };
var assigner = new RandomSpawnAssigner();
SpawnPointInfo Pick( params float[] positions )
{
	GameUtils.Spawns = positions.Select( Spawn ).ToArray();
	return ((ISpawnAssigner)assigner).GetSpawnPoint( owner );
}
void Reset()
{
	GameUtils.PlayerPawns.Clear();
	GameUtils.LightweightBots.Clear();
	GameUtils.ReverseShuffle = false;
	assigner.Scene.Trace.Calls.Clear();
	assigner.Scene.Trace.IsBlocked = (_, _) => true;
	owner.Team = Team.Unassigned;
}
PlayerPawn Human( float x, Team team = Team.Unassigned, bool alive = true, bool valid = true )
{
	var pawn = new PlayerPawn { Client = new Client { Team = team }, Transform = new( new Vector3( x, 0, 0 ) ), Valid = valid };
	pawn.HealthComponent.State = alive ? LifeState.Alive : LifeState.Dead;
	GameUtils.PlayerPawns.Add( pawn );
	return pawn;
}
void Bot( float x, Team team = Team.Unassigned, bool alive = true, bool valid = true ) => GameUtils.LightweightBots.Add(
	new LightweightCombatBot { Team = team, IsAlive = alive, Valid = valid, Transform = new( new Vector3( x, 0, 0 ) ) } );

Reset();
Check( Pick( 100, 200 ).Position.x == 100, "With no enemies, retain the shuffled spawn order." );
GameUtils.ReverseShuffle = true;
Check( Pick( 100, 200 ).Position.x == 200, "Safe spawns must retain random variety." );

Reset();
Human( 0 );
Check( Pick( 100, 400 ).Position.x == 400, "When every spawn is too close, choose the farther one." );
Check( Pick( 400, 100 ).Position.x == 400, "Fallback safety must not depend on candidate order." );
Check( Pick( 200, -200 ).Position.x == 200, "Equal-risk fallback spawns must retain shuffled order." );
GameUtils.ReverseShuffle = true;
Check( Pick( 200, -200 ).Position.x == -200, "Equal-risk fallback spawns must retain random variety." );

Reset();
owner.Team = Team.Terrorist;
Human( 0, Team.CounterTerrorist );
Bot( 1000, Team.Terrorist );
Check( Pick( 1000, 100 ).Position.x == 100, "A free spawn must beat a distant spawn occupied by a friendly bot." );

Reset();
Human( 0 );
assigner.Scene.Trace.IsBlocked = (from, _) => from.x < 0;
Check( Pick( 200, -200 ).Position.x == -200, "At equal enemy distance, prefer cover." );
assigner.Scene.Trace.IsBlocked = (from, _) => from.x == 100;
Check( Pick( 100, 800 ).Position.x == 800, "Avoid nearby enemies before considering cover." );

Reset();
Human( 0 );
assigner.Scene.Trace.IsBlocked = (_, _) => false;
Check( Pick( 600, 1400 ).Position.x == 1400, "If all spawns are exposed, prefer the farther enemy distance." );
Check( assigner.Scene.Trace.Calls.All( ray => ray.From.z == 64 && ray.To.z == 64 ), "Visibility must check body height at both ends, rather than the enemy's feet." );
Check( assigner.Scene.Trace.ExcludedTags.Contains( "trigger" ), "Trigger volumes must not count as cover." );

Reset();
Human( 0 );
Check( Pick( 100, 600 ).Position.x == 600, "A fully safe candidate must beat unsafe candidates." );
Check( Pick( 512 ).Position.x == 512, "An enemy exactly at the configured minimum distance is permitted." );

Reset();
Human( 0, alive: false );
Human( 0, valid: false );
Bot( 0, alive: false );
Bot( 0, valid: false );
Check( Pick( 0, 600 ).Position.x == 0, "Dead and invalid actors must not block spawns." );
var self = Human( 0 );
self.Client = owner;
Check( Pick( 0, 600 ).Position.x == 0, "The respawning pawn must not block its own spawn." );

Reset();
owner.Team = Team.Terrorist;
Human( 100, Team.Terrorist );
Check( Pick( 0, 600 ).Position.x == 0, "Nearby teammates outside the occupancy radius must not count as enemies." );
Human( 0, Team.Terrorist );
Check( Pick( 0, 600 ).Position.x == 600, "Living teammates must still block overlapping spawns." );

Reset();
Bot( 0 );
Check( Pick( 100, 400 ).Position.x == 400, "Enemy bots must influence fallback distance in free-for-all." );
Reset();
Human( 5000 );
Check( Pick( 0 ).Position.x == 0 && assigner.Scene.Trace.Calls.Count == 0, "Distant enemies must not trigger unnecessary visibility traces." );

Reset();
GameUtils.MapFallback = Spawn( 1234 );
Check( Pick().Position.x == 1234, "Missing tagged spawns must use the map fallback without indexing an empty list." );

var teamAssigner = new TeamSpawnAssigner();
SpawnPointInfo PickTeam( params float[] positions )
{
	GameUtils.Spawns = positions.Select( Spawn ).ToArray();
	return teamAssigner.GetSpawnPoint( owner );
}
foreach ( var botOccupant in new[] { false, true } )
foreach ( var reverse in new[] { false, true } )
{
	Reset();
	owner.Team = Team.Terrorist;
	GameUtils.ReverseShuffle = reverse;
	if ( botOccupant ) Bot( 0, Team.Terrorist );
	else Human( 0, Team.Terrorist );
	Human( 10100, Team.CounterTerrorist );
	teamAssigner.Scene.Trace.IsBlocked = (_, _) => false;
	Check( PickTeam( 0, 10000 ).Position.x == 10000,
		"A free team spawn must beat an occupied one even when the free spawn is close to and visible from an enemy." );
}

Reset();
owner.Team = Team.Terrorist;
teamAssigner.Scene.Trace.IsBlocked = (_, _) => true;
Human( 0, Team.CounterTerrorist );
Check( PickTeam( 500, 2000 ).Position.x == 2000, "Free team spawns must retain their enemy-distance ranking." );
teamAssigner.Scene.Trace.IsBlocked = (from, _) => from.x < 0;
Check( PickTeam( 1500, -1500 ).Position.x == -1500, "Free team spawns at equal distance must still prefer cover." );

Reset();
owner.Team = Team.Terrorist;
teamAssigner.Scene.Trace.IsBlocked = (_, _) => true;
Human( 0, Team.Terrorist );
Bot( 2000, Team.Terrorist );
Human( 2100, Team.CounterTerrorist );
Check( PickTeam( 2000, 0 ).Position.x == 0, "When every spawn is occupied, retain the safest available fallback." );

Reset();
owner.Team = Team.Terrorist;
teamAssigner.Scene.Trace.IsBlocked = (_, _) => true;
Human( 0, Team.Terrorist, alive: false );
Bot( 0, Team.Terrorist, alive: false );
Check( PickTeam( 0, 500 ).Position.x == 0, "Dead humans and bots must not occupy team spawns." );
var ownPawn = Human( 0, Team.Terrorist );
ownPawn.Client = owner;
Check( PickTeam( 0, 500 ).Position.x == 0, "A respawning player's old pawn must not occupy their team spawn." );

Reset();
owner.Team = Team.Terrorist;
GameUtils.MapFallback = Spawn( 4321 );
Check( PickTeam().Position.x == 4321, "Missing team spawns must preserve the map fallback." );

Console.WriteLine( $"PASS: {checks} spawn safety checks against the production spawn assigners." );

// Minimal engine seams keep these policy checks offline. Spawn selection and tracing decisions above
// execute the production random and team spawn assigners; only world data, trace hits and shuffle order are supplied here.
namespace Sandbox
{
	public class Component
	{
		public bool Valid { get; set; } = true;
		public Scene Scene { get; } = new();
	}
	public static class Validity { public static bool IsValid( this Component component ) => component?.Valid == true; }
	public sealed class PropertyAttribute : Attribute;
	public sealed class InlineEditorAttribute : Attribute;
	public sealed class TitleAttribute( string title ) : Attribute { public string Title { get; } = title; }
	public class TagSet : List<string>;
	public readonly record struct Vector3( float x, float y, float z )
	{
		public static Vector3 Up => new( 0, 0, 1 );
		public float LengthSquared => x * x + y * y + z * z;
		public float DistanceSquared( Vector3 other ) => (this - other).LengthSquared;
		public float Distance( Vector3 other ) => MathF.Sqrt( DistanceSquared( other ) );
		public static Vector3 operator +( Vector3 a, Vector3 b ) => new( a.x + b.x, a.y + b.y, a.z + b.z );
		public static Vector3 operator -( Vector3 a, Vector3 b ) => new( a.x - b.x, a.y - b.y, a.z - b.z );
		public static Vector3 operator *( Vector3 a, float scale ) => new( a.x * scale, a.y * scale, a.z * scale );
	}
	public readonly record struct Rotation;
	public readonly record struct Transform( Vector3 Position )
	{
		public Transform World => this;
		public Rotation Rotation => default;
	}
	public class Scene { public TraceStub Trace { get; } = new(); }
	public class TraceStub
	{
		public Func<Vector3, Vector3, bool> IsBlocked { get; set; }
		public List<(Vector3 From, Vector3 To)> Calls { get; } = new();
		public string[] ExcludedTags { get; private set; } = [];
		private Vector3 _from, _to;
		public TraceStub FromTo( Vector3 from, Vector3 to ) { _from = from; _to = to; return this; }
		public TraceStub Size( float size ) => this;
		public TraceStub WithoutTags( params string[] tags ) { ExcludedTags = tags; return this; }
		public TraceResult Run() { Calls.Add( (_from, _to) ); return new( IsBlocked( _from, _to ) ); }
	}
	public readonly record struct TraceResult( bool Hit );
	public static class Log { public static void Warning( string message ) { } public static void Info( string message ) { } }
}
namespace Sandbox.Events { }
namespace Facepunch
{
	public class SkirmishArena
	{
		public static SkirmishArena Settled { get; set; }
		public SpawnPointInfo PickSpawn( Team team, object pawn ) => default;
	}
	public enum Team { Unassigned, Terrorist, CounterTerrorist }
	public enum LifeState { Alive, Dead }
	public class Client
	{
		public Team Team { get; set; }
		public string DisplayName { get; set; }
		public PlayerPawn PlayerPawn { get; set; }
		public bool IsFriendly( Client other ) => Team != Team.Unassigned && Team == other.Team;
	}
	public class HealthComponent { public LifeState State { get; set; } }
	public class PlayerPawn : Component
	{
		public Client Client { get; set; }
		public Transform Transform { get; set; }
		public HealthComponent HealthComponent { get; } = new();
		public Vector3 WorldPosition => Transform.Position;
		public Team Team => Client.Team;
		public float TimeSinceLastRespawn { get; set; }
		public List<string> SpawnPointTags { get; } = new();
		public object GameObject => this;
	}
	public class LightweightCombatBot : Component
	{
		public bool IsAlive { get; set; } = true;
		public Team Team { get; set; }
		public Transform Transform { get; set; }
		public Vector3 WorldPosition => Transform.Position;
	}
	public static class GameUtils
	{
		public static List<PlayerPawn> PlayerPawns { get; } = new();
		public static List<LightweightCombatBot> LightweightBots { get; } = new();
		public static SpawnPointInfo[] Spawns { get; set; } = [];
		public static SpawnPointInfo MapFallback { get; set; }
		public static bool ReverseShuffle { get; set; }
		public static IEnumerable<SpawnPointInfo> GetSpawnPoints( params string[] tags ) => Spawns;
		public static IEnumerable<SpawnPointInfo> GetSpawnPoints( Team team, params string[] tags ) => Spawns;
		public static SpawnPointInfo GetRandomSpawnPoint( Team team ) => MapFallback;
		public static IReadOnlyList<T> Shuffle<T>( this IEnumerable<T> items ) => (ReverseShuffle ? items.Reverse() : items).ToArray();
	}
}
