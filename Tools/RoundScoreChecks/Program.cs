global using Sandbox;
using Facepunch;
using Facepunch.UI;
using Sandbox.Events;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
PlayerScore Player() => new() { Client = new Client { IsBot = true } };
void Round( PlayerScore score, params int[] awards )
{
	foreach ( var award in awards ) score.AddScore( award );
	((IGameEventHandler<RoundCounterIncrementedEvent>)score).OnGameEvent( new() );
}

var first = Player();
Round( first, 100 );
Round( first, 0 );
Round( first, 10 );
Check( first.ScoreHistory.SequenceEqual( new[] { 100, 0, 10 } ), "Third-round score must exclude first-round points." );
Check( first.Score == 110, "Recording a round must preserve the match total." );
var second = Player();
Round( second, 0 );
Round( second, 100 );
Round( second, 20 );
Check( new[] { first, second }.OrderBy( score => score.ScoreHistory.LastOrDefault() ).First() == first,
	"Last-round team balancing must prefer the player who earned 10, rather than 20, last round." );

Round( first, 25, -10, -25 );
Check( first.ScoreHistory.Last() == -10, "Round history must include penalties and multiple score awards accurately." );
Round( first );
Check( first.ScoreHistory.Last() == 0, "A round without awards must record zero." );

var totalBeforeRoundReset = first.Score;
((IGameEventHandler<RoundCounterResetEvent>)first).OnGameEvent( new() );
Check( first.ScoreHistory.Count == 0 && first.Score == totalBeforeRoundReset, "Resetting the round counter must clear history while preserving match points." );
Round( first, 15 );
Check( first.ScoreHistory.SequenceEqual( new[] { 15 } ), "A new round sequence must not inherit points from the previous sequence." );

((IGameEventHandler<ResetScoresEvent>)first).OnGameEvent( new() );
Check( first.Score == 0 && first.ScoreHistory.Count == 0, "A full score reset must clear points and history." );
Round( first, 30 );
Check( first.ScoreHistory.SequenceEqual( new[] { 30 } ), "A fresh match must start with a fresh round baseline." );

foreach ( var resetRoundsFirst in new[] { false, true } )
{
	var player = Player();
	Round( player, 200 );
	if ( resetRoundsFirst ) ((IGameEventHandler<RoundCounterResetEvent>)player).OnGameEvent( new() );
	((IGameEventHandler<ResetScoresEvent>)player).OnGameEvent( new() );
	if ( !resetRoundsFirst ) ((IGameEventHandler<RoundCounterResetEvent>)player).OnGameEvent( new() );
	Round( player, 5 );
	Check( player.ScoreHistory.SequenceEqual( new[] { 5 } ), "Full score and round resets must work in either event order." );
}

var random = new Random( 413 );
var longMatch = Player();
var expectedTotal = 0;
for ( var round = 0; round < 50; round++ )
{
	var award = random.Next( -50, 201 );
	Round( longMatch, award );
	expectedTotal += award;
	Check( longMatch.ScoreHistory.Last() == award && longMatch.Score == expectedTotal,
		"Long matches must retain exact per-round contributions and the cumulative score." );
}

Console.WriteLine( $"PASS: {checks} round-score checks against production PlayerScore." );

// Engine services outside score tracking are supplied here; all score changes and round handlers are production code.
namespace Sandbox
{
	public class Component
	{
		public Scene Scene { get; } = new();
		public NetworkState Network { get; } = new();
		public T GetComponent<T>() where T : class => this as T;
		public IEnumerable<T> GetComponentsInChildren<T>() => [];
		protected virtual void OnStart() { }
	}
	public class Scene { public void Dispatch<T>( T args ) { } }
	public class NetworkState { public object Owner => null; }
	public class Connection { public static Connection Host { get; } = new(); }
	public static class Validity { public static bool IsValid( this Component component ) => component is not null; public static int Clamp( this int value, int min, int max ) => Math.Clamp( value, min, max ); }
	public static class Networking { public static bool IsHost => true; }
	public class NetList<T> : List<T>;
	public enum SyncFlags { FromHost }
	public enum NetFlags { HostOnly }
	public sealed class PropertyAttribute : Attribute;
	public sealed class ReadOnlyAttribute : Attribute;
	public sealed class OrderAttribute( int value ) : Attribute { public int Value => value; }
	public sealed class SyncAttribute( SyncFlags flags = default ) : Attribute { public SyncFlags Flags => flags; }
	public static class Rpc
	{
		public static Connection Caller { get; set; }
		public sealed class HostAttribute : Attribute;
		public sealed class OwnerAttribute : Attribute;
		public sealed class BroadcastAttribute( NetFlags flags ) : Attribute { public NetFlags Flags => flags; }
		public static IDisposable FilterInclude( object owner ) => new Filter();
		private class Filter : IDisposable { public void Dispose() { } }
	}
	public class MemberDescription { public string Name => ""; public T GetCustomAttribute<T>() where T : Attribute => null; }
	public class MethodDescription { public T InvokeWithReturn<T>( object target, object args ) => default; }
	public class TypeDescription
	{
		public List<MemberDescription> Members { get; } = new();
		public MethodDescription GetMethod( string name ) => null;
		public object GetValue( object target, string name ) => null;
	}
	public static class TypeLibrary { public static TypeDescription GetType( Type type ) => new(); }
}
namespace Sandbox.Events
{
	public interface IGameEvent;
	public interface IGameEventHandler<T> { void OnGameEvent( T args ); }
}
namespace Facepunch
{
	public enum Team { Unassigned, Terrorist, CounterTerrorist }
	public enum LifeState { Alive, Dead }
	public class Client : Component
	{
		public static Client Local { get; } = new();
		public bool IsBot { get; set; }
		public Connection Connection { get; set; } = new();
		public Team Team { get; set; }
		public PlayerPawn PlayerPawn { get; set; }
		public bool IsFriendly( Client other ) => Team != Team.Unassigned && Team == other.Team;
	}
	public class PlayerPawn : Component { public Client Client { get; set; } public Team Team { get; set; } public HealthComponent HealthComponent { get; } = new(); }
	public class HealthComponent { public LifeState State { get; set; } }
	public class LightweightCombatBot : Component;
	public record DamageInfo( Component Attacker, Component Victim );
	public record KillEvent( DamageInfo DamageInfo );
	public record BombPlantedEvent( PlayerPawn Planter );
	public record BombDefusedEvent( PlayerPawn Defuser );
	public record BombDetonatedEvent;
	public record RoundCounterIncrementedEvent;
	public record RoundCounterResetEvent;
	public record ResetScoresEvent;
	public static class GameUtils
	{
		public static List<PlayerPawn> PlayerPawns { get; } = new();
		public static PlayerPawn GetPlayerFromComponent( Component component ) => component as PlayerPawn;
		public static LightweightCombatBot GetLightweightBotFromComponent( Component component ) => component as LightweightCombatBot;
		public static Team GetTeamFromComponent( Component component ) => (component as PlayerPawn)?.Team ?? Team.Unassigned;
	}
	public class GameSettings { public bool UseScorestreaks { get; set; } }
	public static class GameSettingsSystem { public static GameSettings Current { get; } = new(); }
	public class ScorestreakManager : Component { public static ScorestreakManager Instance => null; public void ActivateUAV( Team team ) { } }
}
