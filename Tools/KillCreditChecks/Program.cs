global using Sandbox;
using Facepunch;
using Sandbox.Events;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}

PlayerPawn Human( Team team = Team.Red, bool bot = false ) => new() { Team = team, Client = new Client { IsBot = bot } };
var resource = new EquipmentResource();
ResourceLibrary.Resource = resource;
var weapon = new Equipment { Resource = resource };
var playerRule = new PlayerStatsRule();
var weaponRule = new WeaponStatsRule();

void Scenario( string label, Component attacker, Component victim, bool awarded, HitboxTags hitbox = HitboxTags.Chest )
{
	Stats.Counts.Clear();
	WeaponStats.Counts.Clear();
	Progression.Xp = WeaponProgression.Xp = UsageStats.Kills = DailyChallenges.Kills = DailyChallenges.Headshots = 0;
	var info = new DamageInfo( attacker, victim, weapon, hitbox, DamageFlags.WallBang );
	((IGameEventHandler<KillEvent>)playerRule).OnGameEvent( new( info ) );
	((IGameEventHandler<KillEvent>)weaponRule).OnGameEvent( new( info ) );
	var headshot = hitbox.HasFlag( HitboxTags.Head );
	Check( Stats.Get( "kills" ) == (awarded ? 1 : 0), $"{label}: player kill credit." );
	Check( WeaponStats.Get( "kills" ) == (awarded ? 1 : 0), $"{label}: weapon kill credit." );
	Check( Progression.Xp == (awarded ? headshot ? 150 : 100 : 0), $"{label}: player XP." );
	Check( WeaponProgression.Xp == (awarded ? headshot ? 75 : 50 : 0), $"{label}: weapon XP." );
	Check( DailyChallenges.Kills == (awarded ? 1 : 0) && UsageStats.Kills == (awarded ? 1 : 0), $"{label}: challenge and usage progress." );
	Check( Stats.Get( "kills-headshots" ) == (awarded && headshot ? 1 : 0)
		&& WeaponStats.Get( "kills-headshots" ) == (awarded && headshot ? 1 : 0)
		&& DailyChallenges.Headshots == (awarded && headshot ? 1 : 0), $"{label}: headshot credit across stats and challenges." );
	Check( WeaponStats.LastFlags == (awarded ? DamageFlags.WallBang : DamageFlags.None), $"{label}: valid kills must retain extra damage flags." );
	WeaponStats.LastFlags = DamageFlags.None;
}

Scenario( "Friendly human", Human(), Human(), false );
Scenario( "Friendly lightweight bot", Human(), new LightweightCombatBot { Team = Team.Red }, false );
var self = Human();
Scenario( "Suicide", self, self, false );
var ffaSelf = Human( Team.Unassigned );
Scenario( "Free-for-all suicide", ffaSelf, ffaSelf, false );
Scenario( "Non-operator target", Human(), new Component(), false );
Scenario( "Missing target", Human(), null, false );
Scenario( "Enemy human", Human(), Human( Team.Blue ), true );
Scenario( "Enemy lightweight bot", Human(), new LightweightCombatBot { Team = Team.Blue }, true );
Scenario( "Free-for-all human", Human( Team.Unassigned ), Human( Team.Unassigned ), true );
Scenario( "Free-for-all lightweight bot", Human( Team.Unassigned ), new LightweightCombatBot(), true );
Scenario( "Headshot", Human(), Human( Team.Blue ), true, HitboxTags.Head );
Scenario( "Headshot with additional tags", Human(), Human( Team.Blue ), true, HitboxTags.Head | HitboxTags.Neck );
Scenario( "Neck shot is not a headshot", Human(), Human( Team.Blue ), true, HitboxTags.Neck );
Scenario( "Bot-owned pawn cannot earn local rewards", Human( bot: true ), Human( Team.Blue ), false );
Scenario( "Lightweight bot attacker cannot earn local rewards", new LightweightCombatBot(), Human(), false );
Scenario( "Missing attacker", null, Human(), false );
var childOwner = Human();
var victimOwner = Human( Team.Blue );
Scenario( "Child attacker and victim components", new Component { Player = childOwner }, new Component { Player = victimOwner }, true );
Scenario( "Suicide via child components", new Component { Player = childOwner }, new Component { Player = childOwner }, false );
var disconnected = Human();
disconnected.Client = null;
Scenario( "Disconnected attacker", disconnected, Human( Team.Blue ), false );
Scenario( "Invalid victim", Human(), new PlayerPawn { Valid = false }, false );
Networking.IsHost = false;
Scenario( "Non-host event cannot award duplicate credit", Human(), Human( Team.Blue ), false );
Networking.IsHost = true;

foreach ( var attacker in new Component[] { Human( Team.Blue ), new LightweightCombatBot(), new Component(), null } )
{
	Stats.Counts.Clear();
	((IGameEventHandler<KillEvent>)playerRule).OnGameEvent( new( new( attacker, Human(), null, HitboxTags.Chest, DamageFlags.None ) ) );
	Check( Stats.Get( "deaths" ) == 1, "Human deaths must be recorded regardless of whether the attacker was a player, bot, or world damage." );
}

Console.WriteLine( $"PASS: {checks} kill credit checks against production player and weapon stat rules." );

namespace Sandbox
{
	public class Component
	{
		public bool Valid { get; set; } = true;
		public Facepunch.PlayerPawn Player { get; set; }
		public Facepunch.LightweightCombatBot Bot { get; set; }
		private readonly GameObject _gameObject = new();
		public GameObject GameObject => Player?.GameObject ?? Bot?.GameObject ?? _gameObject;
		public NetworkState Network { get; } = new();
	}
	public class GameObject { public GameObject Root => this; }
	public static class Networking { public static bool IsHost { get; set; } = true; }
	public class NetworkState { public object Owner => null; }
	public static class Validity { public static bool IsValid( this Component value ) => value?.Valid == true; }
	public enum NetFlags { HostOnly }
	public static class Rpc
	{
		public sealed class BroadcastAttribute( NetFlags flags ) : Attribute { public NetFlags Flags => flags; }
		public static IDisposable FilterInclude( object connection ) => new Filter();
		private class Filter : IDisposable { public void Dispose() { } }
	}
	public static class ResourceLibrary
	{
		public static Facepunch.EquipmentResource Resource;
		public static T Get<T>( string path ) where T : class => Resource as T;
	}
}
namespace Sandbox.Events { public interface IGameEventHandler<T> { void OnGameEvent( T args ); } }
namespace Facepunch
{
	public enum Team { Unassigned, Red, Blue }
	[Flags] public enum HitboxTags { None = 0, Head = 1, Chest = 2, Neck = 512 }
	[Flags] public enum DamageFlags { None = 0, WallBang = 64 }
	public record DamageInfo( Component Attacker, Component Victim, Component Inflictor, HitboxTags Hitbox, DamageFlags Flags );
	public record KillEvent( DamageInfo DamageInfo );
	public class Client : Component { public bool IsBot { get; set; } }
	public class PlayerPawn : Component { public Client Client { get; set; } public Team Team { get; set; } }
	public class LightweightCombatBot : Component { public Team Team { get; set; } }
	public class Equipment : Component { public EquipmentResource Resource { get; set; } }
	public class EquipmentResource : Component { public string ResourcePath => "test.equip"; }
	public static class GameUtils
	{
		public static PlayerPawn GetPlayerFromComponent( Component component ) => component.IsValid() ? component as PlayerPawn ?? component.Player : null;
		public static LightweightCombatBot GetLightweightBotFromComponent( Component component ) => component.IsValid() ? component as LightweightCombatBot ?? component.Bot : null;
		public static Team GetTeamFromComponent( Component component ) => GetPlayerFromComponent( component )?.Team ?? GetLightweightBotFromComponent( component )?.Team ?? Team.Unassigned;
	}
	public static class Stats
	{
		public static Dictionary<string, int> Counts { get; } = new();
		public static void Increment( string name ) => Counts[name] = Get( name ) + 1;
		public static int Get( string name ) => Counts.GetValueOrDefault( name );
	}
	public static class WeaponStats
	{
		public static Dictionary<string, int> Counts { get; } = new();
		public static DamageFlags LastFlags;
		public static void Increment( string name, EquipmentResource resource, DamageFlags flags ) { Counts[name] = Get( name ) + 1; LastFlags = flags; }
		public static int Get( string name ) => Counts.GetValueOrDefault( name );
	}
	public static class Progression { public static int Xp; public static void AddXP( int amount ) => Xp += amount; }
	public static class WeaponProgression { public static int Xp; public static void AddXP( EquipmentResource resource, int amount ) => Xp += amount; }
	public static class UsageStats { public static int Kills; public static void CountKill( EquipmentResource resource ) => Kills++; }
	public static class DailyChallenges { public static int Kills, Headshots; public static void OnKill( bool headshot ) { Kills++; if ( headshot ) Headshots++; } }
}
