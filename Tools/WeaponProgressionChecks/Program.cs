global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var rifle = new EquipmentResource { ResourceName = "rifle" };
var pistol = new EquipmentResource { ResourceName = "pistol" };
ResourceLibrary.Weapons.AddRange( [rifle, pistol] );
string Xp( EquipmentResource resource ) => $"hc1.weapon.xp.{resource.ResourceName}";
string Lifetime( EquipmentResource resource ) => $"hc1.weapon.max_xp.{resource.ResourceName}";

var legacyXp = WeaponProgression.GetXPForLevel( 12 );
Game.Cookies.Set( Xp( rifle ), legacyXp );
Check( WeaponProgression.GetLifetimeXP( rifle ) >= legacyXp, "Legacy saves without a lifetime cookie must retain their known weapon XP." );
Check( WeaponProgression.GetLifetimeLevel( rifle ) >= 12, "Camo unlocks must not fall below an already-earned current weapon level." );
WeaponProgression.AddXP( rifle, 50 );
Check( WeaponProgression.GetXP( rifle ) == legacyXp + 50 && WeaponProgression.GetLifetimeXP( rifle ) == legacyXp + 50,
	"The next award must migrate legacy progression without dropping earned XP." );

Game.Cookies.Set( Xp( pistol ), WeaponProgression.GetXPForLevel( 8 ) );
Game.Cookies.Set( "hc1.progress.xp", Progression.GetXPForLevel( Progression.MaxLevel ) );
var beforeRifle = WeaponProgression.GetLifetimeXP( rifle );
var beforePistol = WeaponProgression.GetXP( pistol );
Progression.EnterPrestigeMode();
Check( Progression.GetPrestige() == 1 && Progression.GetXP() == 0, "Eligible prestige must keep its existing player reset behaviour." );
Check( WeaponProgression.GetLevel( rifle ) == 1 && WeaponProgression.GetLevel( pistol ) == 1,
	"Prestige must still reset current weapon levels and attachment progression." );
Check( WeaponProgression.GetLifetimeXP( rifle ) == beforeRifle && WeaponProgression.GetLifetimeXP( pistol ) == beforePistol,
	"Prestige must preserve lifetime XP, including weapons whose lifetime cookie was missing." );
Check( Game.Cookies.Get( Lifetime( pistol ), 0 ) == beforePistol, "Lifetime progress must be persisted before clearing the old weapon XP." );
WeaponProgression.AddXP( rifle, 50 );
Check( WeaponProgression.GetXP( rifle ) == 50 && WeaponProgression.GetLifetimeXP( rifle ) == beforeRifle + 50,
	"Post-prestige weapon XP must continue contributing to lifetime progression." );

var maximum = WeaponProgression.GetXPForLevel( WeaponProgression.MaxLevel );
foreach ( var current in new[] { 0, 100, maximum - 1, maximum, int.MaxValue } )
foreach ( var award in new[] { 1, 75, int.MaxValue } )
{
	Game.Cookies.Set( Xp( rifle ), current );
	Game.Cookies.Set( Lifetime( rifle ), current );
	WeaponProgression.AddXP( rifle, award );
	var expected = (int)Math.Min( (long)current + award, maximum );
	Check( WeaponProgression.GetXP( rifle ) == expected && WeaponProgression.GetLifetimeXP( rifle ) == expected,
		"Large awards must saturate both XP totals without integer overflow or negative progress." );
}

Game.Cookies.Set( Xp( rifle ), -10 );
Game.Cookies.Set( Lifetime( rifle ), -50 );
WeaponProgression.AddXP( rifle, 50 );
Check( WeaponProgression.GetXP( rifle ) == 50 && WeaponProgression.GetLifetimeXP( rifle ) == 50,
	"Negative saved XP must recover to a valid positive award." );
var writes = Game.Cookies.Writes;
WeaponProgression.AddXP( rifle, 0 );
WeaponProgression.AddXP( rifle, -1 );
WeaponProgression.AddXP( null, 100 );
Check( Game.Cookies.Writes == writes, "Invalid awards and missing weapons must not write progress." );

Game.Cookies.Set( "hc1.progress.xp", 0 );
Game.Cookies.Set( Xp( pistol ), 1234 );
Progression.EnterPrestigeMode();
Check( WeaponProgression.GetXP( pistol ) == 1234, "Ineligible prestige attempts must not reset weapons." );
Game.Cookies.Set( "hc1.progress.xp", Progression.GetXPForLevel( Progression.MaxLevel ) );
Game.Cookies.Set( "hc1.progress.prestige", 10 );
Progression.EnterPrestigeMode();
Check( WeaponProgression.GetXP( pistol ) == 1234, "Maximum-prestige profiles must not reset weapons again." );

Console.WriteLine( $"PASS: {checks} weapon progression and prestige checks against production code." );

// Tests use an in-memory profile. No real game cookies, Steam account, or editor is accessed.
namespace Sandbox
{
	public static class Game { public static ulong SteamId => 0; public static CookieStore Cookies { get; } = new(); }
	public class CookieStore
	{
		private readonly Dictionary<string, object> _values = new();
		public int Writes;
		public T Get<T>( string key, T fallback ) => _values.TryGetValue( key, out var value ) ? (T)value : fallback;
		public void Set<T>( string key, T value ) { _values[key] = value; Writes++; }
	}
	public static class ResourceLibrary
	{
		public static List<EquipmentResource> Weapons { get; } = new();
		public static IEnumerable<T> GetAll<T>() => Weapons.OfType<T>();
	}
	public class Component;
	public static class Validity { public static bool IsValid( this Component component ) => component is not null; }
}
namespace Facepunch
{
	public class EquipmentResource { public string ResourceName { get; set; } }
	public class Client : Component { public static Client Local => null; public void RpcUpdatePrestige( int value ) { } }
}
namespace Facepunch.Gunsmith { public static class GunsmithLoadoutManager { public static void MarkChanged() { } } }
