global using Sandbox;
using Facepunch;
using Sandbox.Events;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var playerRule = new PlayerStatsRule();
var weaponRule = new WeaponStatsRule();
var resource = new EquipmentResource { ResourceName = "rifle", ResourcePath = "weapons/rifle.equipment" };
ResourceLibrary.Resource = resource;
var weapon = new Equipment { Resource = resource };
var killer = new PlayerPawn( Team.Red, "killer" );
var victim = new PlayerPawn( Team.Blue, "victim" );
DamageInfo Hit( Component attacker, Component target, HitboxTags hitbox = HitboxTags.Chest, DamageFlags flags = DamageFlags.None )
	=> new( attacker, target, weapon, hitbox, flags );
void Record( DamageInfo damage )
{
	Ledger.Entries.Clear();
	var killed = new KillEvent( damage );
	((IGameEventHandler<KillEvent>)playerRule).OnGameEvent( killed );
	((IGameEventHandler<KillEvent>)weaponRule).OnGameEvent( killed );
}
int Value( PlayerPawn player, string key ) => Ledger.Read( player.Network.Owner, key );
void NoKillCredit( string label )
{
	Check( Value( killer, "kills" ) == 0 && Value( killer, "career-xp" ) == 0 && Value( killer, "daily-kills" ) == 0,
		$"{label}: no career kills, XP or daily challenge progress." );
	Check( Value( killer, "kills-rifle" ) == 0 && Value( killer, "weapon-xp" ) == 0 && Value( killer, "usage-kills" ) == 0,
		$"{label}: no weapon kills, XP or usage credit." );
}

Record( Hit( killer, victim ) );
Check( Value( killer, "kills" ) == 1 && Value( killer, "career-xp" ) == 100 && Value( killer, "daily-kills" ) == 1,
	"An enemy kill must award the existing career XP and daily progress." );
Check( Value( killer, "kills-rifle" ) == 1 && Value( killer, "weapon-xp" ) == 50 && Value( killer, "usage-kills" ) == 1,
	"An enemy kill must award the existing weapon XP and usage credit." );
Check( Value( victim, "deaths" ) == 1 && Value( killer, "deaths" ) == 0, "Death credit must target only the victim's connection." );

Record( Hit( killer, victim, HitboxTags.Head | HitboxTags.Neck, DamageFlags.WallBang ) );
Check( Value( killer, "kills-headshots" ) == 1 && Value( killer, "career-xp" ) == 150 && Value( killer, "daily-headshots" ) == 1,
	"A combined hitbox mask containing Head must retain headshot career rewards." );
Check( Value( killer, "kills-headshots-rifle" ) == 1 && Value( killer, "weapon-xp" ) == 75,
	"A combined head hit must retain headshot weapon rewards." );
Check( Value( killer, "kills-wallbang-rifle" ) == 1, "Eligible kills must preserve weapon damage-flag statistics." );

victim.Team = Team.Red;
Record( Hit( killer, victim, HitboxTags.Head ) );
NoKillCredit( "Team kill" );
Check( Value( victim, "deaths" ) == 1, "A team kill must still record the victim's death." );
victim.Team = Team.Blue;
Record( Hit( killer, killer ) );
NoKillCredit( "Suicide" );
Check( Value( killer, "deaths" ) == 1, "A suicide must count one death without kill rewards." );

killer.Team = Team.Unassigned;
victim.Team = Team.Unassigned;
Record( Hit( killer, victim ) );
Check( Value( killer, "kills" ) == 1 && Value( killer, "kills-rifle" ) == 1, "Different unassigned players must still count as enemies in free-for-all." );
killer.Team = Team.Red;
victim.Team = Team.Blue;

var bot = new LightweightCombatBot( Team.Blue );
Record( Hit( killer, bot ) );
Check( Value( killer, "kills" ) == 1 && Value( killer, "weapon-xp" ) == 50, "Enemy lightweight bots must remain eligible kill targets." );
bot.Team = Team.Red;
Record( Hit( killer, bot ) );
NoKillCredit( "Friendly lightweight bot" );
Record( Hit( bot, victim ) );
Check( Value( victim, "deaths" ) == 1, "Deaths to lightweight bots must count in the career record." );

var legacyBot = new PlayerPawn( Team.Red, "legacy bot" );
legacyBot.Client.IsBot = true;
Record( Hit( legacyBot, victim ) );
Check( Value( legacyBot, "kills" ) == 0 && Value( legacyBot, "weapon-xp" ) == 0 && Value( victim, "deaths" ) == 1,
	"Bot-controlled pawns must not award the host progress, while their human victims still receive deaths." );

Record( Hit( null, victim ) );
Check( Value( victim, "deaths" ) == 1, "World damage with no attacker must count the victim's death." );
NoKillCredit( "World damage" );
Record( Hit( killer, new Component() ) );
NoKillCredit( "Destroyed prop" );

var childAttacker = new Component { GameObject = killer.GameObject };
var childVictim = new Component { GameObject = victim.GameObject };
Record( Hit( childAttacker, childVictim ) );
Check( Value( killer, "kills" ) == 1 && Value( victim, "deaths" ) == 1, "Child health/attacker components must resolve to their owning players." );
Record( Hit( killer, new Component { GameObject = killer.GameObject } ) );
NoKillCredit( "Self damage through child health" );

killer.Client.Valid = false;
Record( Hit( killer, victim ) );
NoKillCredit( "Disconnected attacker" );
Check( Value( victim, "deaths" ) == 1, "A disconnected attacker must not prevent death bookkeeping." );
killer.Client.Valid = true;
Networking.IsHost = false;
Record( Hit( killer, victim ) );
Check( Ledger.Entries.Count == 0, "Non-host kill notifications must never issue duplicate progress/death RPCs." );
Networking.IsHost = true;
Record( Hit( killer, null ) );
NoKillCredit( "Missing victim" );

Console.WriteLine( $"PASS: {checks} career and weapon kill-stat checks against production rules." );

// Only engine/network routing and persistent progress sinks are replaced. Eligibility, event handling,
// owner filtering, headshot decisions and weapon-stat expansion execute the production code above.
namespace Sandbox
{
	public class Component
	{
		public bool Valid { get; set; } = true;
		public GameObject GameObject { get; set; } = new();
		public NetworkState Network { get; set; } = new();
	}
	public class GameObject
	{
		public GameObject Root => this;
		public Facepunch.PlayerPawn Player { get; set; }
		public Facepunch.LightweightCombatBot Bot { get; set; }
	}
	public record Connection( string Name );
	public class NetworkState { public Connection Owner { get; set; } }
	public static class Validity { public static bool IsValid( this Component component ) => component?.Valid == true; }
	public static class Networking { public static bool IsHost { get; set; } = true; }
	public sealed class PropertyAttribute : Attribute;
	public enum NetFlags { HostOnly }
	public static class Rpc
	{
		public static Connection Recipient { get; private set; }
		public sealed class BroadcastAttribute( NetFlags flags ) : Attribute { public NetFlags Flags { get; } = flags; }
		public static IDisposable FilterInclude( Connection owner ) => new Filter( owner );
		private sealed class Filter : IDisposable
		{
			private readonly Connection _previous = Recipient;
			public Filter( Connection owner ) { Recipient = owner; }
			public void Dispose() => Recipient = _previous;
		}
	}
	public static class ResourceLibrary
	{
		public static Facepunch.EquipmentResource Resource { get; set; }
		public static T Get<T>( string path ) where T : class => Resource.ResourcePath == path ? Resource as T : null;
	}
}
namespace Sandbox.Events
{
	public interface IGameEventHandler<T> { void OnGameEvent( T eventArgs ); }
}
namespace Facepunch
{
	public enum Team { Unassigned, Red, Blue }
	[Flags] public enum HitboxTags { None = 0, Head = 1, Neck = 2, Chest = 4 }
	[Flags] public enum DamageFlags { None = 0, WallBang = 1, AirShot = 2 }
	public record DamageInfo( Component Attacker, Component Victim, Component Inflictor, HitboxTags Hitbox, DamageFlags Flags );
	public record KillEvent( DamageInfo DamageInfo );
	public class Client : Component { public bool IsBot { get; set; } }
	public class PlayerPawn : Component
	{
		public Team Team { get; set; }
		public Client Client { get; } = new();
		public PlayerPawn( Team team, string owner ) { Team = team; Network.Owner = new( owner ); GameObject.Player = this; }
	}
	public class LightweightCombatBot : Component
	{
		public Team Team { get; set; }
		public LightweightCombatBot( Team team ) { Team = team; GameObject.Bot = this; }
	}
	public class EquipmentResource : Component { public string ResourceName { get; set; } public string ResourcePath { get; set; } }
	public class Equipment : Component { public EquipmentResource Resource { get; set; } }
	public static class GameUtils
	{
		public static PlayerPawn GetPlayerFromComponent( Component component ) => component.IsValid() ? component.GameObject.Player : null;
		public static LightweightCombatBot GetLightweightBotFromComponent( Component component ) => component.IsValid() ? component.GameObject.Bot : null;
		public static Team GetTeamFromComponent( Component component ) => GetPlayerFromComponent( component )?.Team
			?? GetLightweightBotFromComponent( component )?.Team ?? Team.Unassigned;
	}
	public static class Ledger
	{
		public static Dictionary<(Connection, string), int> Entries { get; } = new();
		public static int Read( Connection owner, string key ) => Entries.GetValueOrDefault( (owner, key) );
		public static void Add( string key, int amount = 1 ) => Entries[(Rpc.Recipient, key)] = Read( Rpc.Recipient, key ) + amount;
	}
	public static class Stats
	{
		public static void Increment( string key, double amount = 1 ) => Ledger.Add( key, (int)amount );
		public static double Get( string key, double fallback = 0 ) => Ledger.Read( Rpc.Recipient, key );
	}
	public static class Progression { public static void AddXP( int amount ) => Ledger.Add( "career-xp", amount ); }
	public static class WeaponProgression { public static void AddXP( EquipmentResource resource, int amount ) => Ledger.Add( "weapon-xp", amount ); }
	public static class UsageStats { public static void CountKill( EquipmentResource resource ) => Ledger.Add( "usage-kills" ); }
	public static class DailyChallenges
	{
		public static void OnKill( bool headshot ) { Ledger.Add( "daily-kills" ); if ( headshot ) Ledger.Add( "daily-headshots" ); }
	}
}
