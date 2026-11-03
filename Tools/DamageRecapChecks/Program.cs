global using Sandbox;
using Facepunch;
using Sandbox.Events;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var local = new PlayerPawn { Client = new Client() };
Client.Local = local.Client;
var enemy = new PlayerPawn { Client = new Client() };
var other = new PlayerPawn { Client = new Client() };
var bot = new Component();
var tracker = new DamageTracker();
void Hit( Component attacker, Component victim, float damage ) =>
	((IGameEventHandler<DamageTakenGlobalEvent>)tracker).OnGameEvent( new( new( attacker, victim, damage ) ) );

Hit( local, enemy, 10 );
Hit( local, enemy, 15 );
Hit( local, other, 20 );
Check( tracker.GetMyInflictedDamage( local.Client ).Count == 3, "Damage dealt by the local player must be retrievable using their own client." );
var dealt = tracker.GetGroupedInflictedDamage( local.Client );
Check( dealt.Count == 2 && dealt.Any( row => row.Count == 2 && row.Damage == 25 ) && dealt.Any( row => row.Count == 1 && row.Damage == 20 ),
	"Damage dealt must group by target, not merge every hit under the local attacker." );
Check( dealt.Any( row => row.Victim == enemy && row.Damage == 25 ) && dealt.Any( row => row.Victim == other && row.Damage == 20 ),
	"Each outgoing recap row must carry the correct target for its name label." );
Check( tracker.GetMyInflictedDamage( enemy.Client ).Count == 0, "Opponent clients must not own the local player's inflicted-damage history." );

Hit( local, bot, 30 );
Check( tracker.GetMyInflictedDamage( local.Client ).Count == 4 && tracker.GetGroupedInflictedDamage( local.Client ).Count == 3,
	"Targets without a client, including lightweight bots, must appear in inflicted damage." );
Check( tracker.GetGroupedInflictedDamage( local.Client ).Any( row => row.Victim == bot && row.Damage == 30 ),
	"Bot damage rows must identify the bot target." );
Hit( new Component { Player = local }, new Component { Player = enemy }, 5 );
Check( tracker.GetMyInflictedDamage( local.Client ).Count == 5 && tracker.GetDamageInflictedTo( enemy.Client ).Count == 3,
	"Child components must resolve their player owners for both directions of tracking." );
Check( tracker.GetGroupedInflictedDamage( local.Client ).Single( row => row.Victim == enemy ).Damage == 30,
	"Child-component hits must merge into the same target's existing recap row." );

Hit( enemy, local, 30 );
Hit( enemy, local, 20 );
Hit( bot, local, 10 );
Check( tracker.GetDamageOnMe().Count == 3, "Incoming damage must remain separate from outgoing damage." );
var received = tracker.GetGroupedDamage( local.Client );
Check( received.Count == 2 && received.Any( row => row.Attacker == enemy && row.Count == 2 && row.Damage == 50 )
	&& received.Any( row => row.Attacker == bot && row.Count == 1 && row.Damage == 10 ), "Incoming damage must retain attacker names and hit totals." );
Hit( other, enemy, 7 );
Check( tracker.GetMyInflictedDamage( local.Client ).Count == 5, "Other players' hits must not inflate the local damage dealt." );
Hit( null, local, 6 );
Check( tracker.GetDamageOnMe().Count == 4, "World damage must remain visible in damage taken." );

tracker.ClearBetweenRounds = false;
((IGameEventHandler<BetweenRoundCleanupEvent>)tracker).OnGameEvent( new() );
Check( tracker.GetDamageOnMe().Count == 4, "Disabled round cleanup must preserve the configured history." );
tracker.ClearBetweenRounds = true;
((IGameEventHandler<BetweenRoundCleanupEvent>)tracker).OnGameEvent( new() );
Check( tracker.Registry.Count == 0 && tracker.MyInflictedDamage.Count == 0, "Round cleanup must clear both directions." );

Hit( local, enemy, 8 );
tracker.ClearOnRespawn = false;
((IGameEventHandler<PlayerSpawnedEvent>)tracker).OnGameEvent( new( local ) );
Check( tracker.GetMyInflictedDamage( local.Client ).Count == 1, "Disabled respawn cleanup must preserve history." );
tracker.ClearOnRespawn = true;
((IGameEventHandler<PlayerSpawnedEvent>)tracker).OnGameEvent( new( local ) );
Check( tracker.Registry.Count == 0 && tracker.MyInflictedDamage.Count == 0, "Enabled respawn cleanup must clear both directions." );

Client.Local = null;
Hit( null, local, 5 );
Check( tracker.MyInflictedDamage.Count == 0, "A missing local client must not create a null outgoing-history key." );

Console.WriteLine( $"PASS: {checks} death recap checks against production DamageTracker." );

namespace Sandbox
{
	public class Component { public PlayerPawn Player { get; set; } public NetworkState Network { get; } = new(); }
	public class NetworkState { public object Owner => null; }
	public static class Validity { public static bool IsValid( this Component component ) => component is not null; }
	public sealed class PropertyAttribute : Attribute;
	public enum NetFlags { HostOnly }
	public static class Rpc
	{
		public sealed class BroadcastAttribute( NetFlags flags ) : Attribute { public NetFlags Flags => flags; }
		public static IDisposable FilterInclude( object connection ) => new Filter();
		private class Filter : IDisposable { public void Dispose() { } }
	}
}
namespace Sandbox.Events { public interface IGameEventHandler<T> { void OnGameEvent( T args ); } }
namespace Facepunch
{
	public class Client : Component { public static Client Local { get; set; } }
	public class Pawn : Component { public Client Client { get; set; } }
	public class PlayerPawn : Pawn;
	public record DamageInfo( Component Attacker, Component Victim, float Damage );
	public record DamageTakenGlobalEvent( DamageInfo DamageInfo );
	public record BetweenRoundCleanupEvent;
	public record PlayerSpawnedEvent( PlayerPawn Player );
	public static class GameUtils { public static PlayerPawn GetPlayerFromComponent( Component component ) => component as PlayerPawn ?? component?.Player; }
}
