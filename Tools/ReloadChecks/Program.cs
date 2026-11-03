global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
TestReloadable Gun( int loaded = 0, int reserve = 90 )
{
	Input.UseHeld = false;
	SWB.Base.WeaponSettings.Instance = null;
	return new() { AmmoComponent = new() { Ammo = loaded, ReserveAmmo = reserve, MaxAmmo = 30 } };
}
void Advance( TestReloadable gun, float seconds ) { Time.Now += seconds; gun.Tick(); }

var gun = Gun();
Check( gun.TryReloadEmpty() && gun.IsReloading, "An empty gun with spare rounds must begin reloading." );
Check( gun.AmmoComponent.Ammo == 0 && gun.AmmoComponent.ReserveAmmo == 90, "Starting a reload must not immediately grant rounds." );
Advance( gun, .5f );
Check( !gun.TryReloadEmpty(), "Holding the empty trigger must not restart a running reload." );
Advance( gun, 1.51f );
Check( !gun.IsReloading && gun.AmmoComponent.Ammo == 30 && gun.AmmoComponent.ReserveAmmo == 60,
	"The existing empty reload duration must fill one magazine and consume exactly its rounds." );
Check( gun.AmmoComponent.ChamberedRounds == 1 && gun.AmmoComponent.Ammo == 30,
	"An empty reload must not manufacture the tactical reload's extra round." );

gun = Gun( reserve: 5 );
Check( gun.TryReloadEmpty(), "A partial reserve must still permit automatic reloading." );
Advance( gun, 2.01f );
Check( gun.AmmoComponent.Ammo == 5 && gun.AmmoComponent.ReserveAmmo == 0, "A nearly empty reserve must yield a partial magazine without creating ammunition." );
gun = Gun( reserve: 0 );
Check( !gun.TryReloadEmpty() && !gun.IsReloading, "No spare ammo must leave the existing dry-fire path available." );
gun = Gun( loaded: 1 );
Check( !gun.TryReloadEmpty(), "Automatic reloading must never interrupt a gun with rounds still loaded." );
gun = Gun();
Input.UseHeld = true;
Check( !gun.TryReloadEmpty(), "Interacting with Use must retain priority over automatic reloading." );
gun = Gun();
SWB.Base.WeaponSettings.Instance = new() { AutoReload = false };
Check( !gun.TryReloadEmpty(), "The existing host auto-reload setting must be respected." );
SWB.Base.WeaponSettings.Instance.AutoReload = true;
Check( gun.TryReloadEmpty(), "Enabling the host setting must allow automatic reloading." );

foreach ( var restriction in new[] { "holstered", "remote", "frozen", "climbing", "locked", "invalid equipment", "invalid owner", "missing ammo" } )
{
	gun = Gun();
	switch ( restriction )
	{
		case "holstered": gun.Weapon.IsDeployed = false; break;
		case "remote": gun.Weapon.Owner.IsLocallyControlled = false; break;
		case "frozen": gun.Weapon.Owner.IsFrozen = true; break;
		case "climbing": gun.Weapon.Owner.IsPipeClimbing = true; break;
		case "locked": gun.Weapon.Tags.Add( "no_shooting" ); break;
		case "invalid equipment": gun.Weapon.Valid = false; break;
		case "invalid owner": gun.Weapon.Owner.Valid = false; break;
		case "missing ammo": gun.AmmoComponent = null; break;
	}
	Check( !gun.TryReloadEmpty() && !gun.IsReloading, $"Automatic reloading must not begin when {restriction}." );
}

// Automatic reloads share the real reload lifecycle, including attachments and shell-by-shell closing time.
gun = Gun();
gun.Weapon.AttachmentReloadMultiplier = .5f;
gun.Weapon.ReloadMagazine = new() { EmptyReloadTime = 4f };
Check( gun.TryReloadEmpty(), "Fitted magazines must support automatic reloading." );
gun.Weapon.AttachmentReloadMultiplier = 2f;
Advance( gun, 1f );
Check( gun.IsReloading && gun.AmmoComponent.Ammo == 0, "The fitted magazine's reload must not finish early." );
Advance( gun, 1.01f );
Check( !gun.IsReloading && gun.AmmoComponent.Ammo == 30, "The captured attachment speed must remain fixed throughout the reload." );

gun = Gun( reserve: 3 );
gun.SingleReload = true;
gun.ReloadExitTime = .5f;
Check( gun.TryReloadEmpty(), "Shell-by-shell weapons must support an empty trigger reload." );
Advance( gun, 2.01f );
Check( gun.IsReloading && gun.AmmoComponent.Ammo == 1 && gun.AmmoComponent.ReserveAmmo == 2, "The first shell must use the empty-reload timing." );
Advance( gun, 1.01f );
Advance( gun, 1.01f );
Check( gun.IsReloading && gun.AmmoComponent.Ammo == 3 && gun.AmmoComponent.ReserveAmmo == 0, "The final available shell must retain the closing animation lockout." );
Advance( gun, .51f );
Check( !gun.IsReloading && gun.AmmoComponent.Ammo == 3, "Closing a shell reload must not add any extra ammunition." );

gun = Gun( loaded: 5, reserve: 30 );
gun.ManualReload();
Advance( gun, 1.01f );
Check( gun.AmmoComponent.Ammo == 31 && gun.AmmoComponent.ReserveAmmo == 4, "Manual tactical reloads must retain their chambered extra round." );

Console.WriteLine( $"PASS: {checks} checks against production reload and ammunition code." );

// Engine seams keep the production reload/ammunition lifecycle runnable without launching s&box.
namespace Sandbox
{
	public class Component
	{
		public bool Valid { get; set; } = true;
		public bool IsProxy { get; set; }
		public GameObject GameObject { get; } = new();
		public ComponentLookup Components { get; } = new();
	}
	public class GameObject { public void PlaySound( SoundEvent sound ) { } }
	public class ComponentLookup { public T Get<T>( FindMode mode ) where T : class => null; }
	public enum FindMode { InParent }
	public static class Validity { public static bool IsValid( this object item ) => item is Component component ? component.Valid : item is not null; }
	public sealed class PropertyAttribute : Attribute;
	public sealed class SyncAttribute : Attribute;
	public sealed class TitleAttribute( string name ) : Attribute { public string Name { get; } = name; }
	public sealed class GroupAttribute( string name ) : Attribute { public string Name { get; } = name; }
	public static class Rpc { public sealed class OwnerAttribute : Attribute; }
	public class SoundEvent;
	public static class Time { public static float Now { get; set; } }
	public readonly record struct TimeUntil( float End )
	{
		public static implicit operator TimeUntil( float seconds ) => new( Time.Now + seconds );
		public static implicit operator bool( TimeUntil time ) => Time.Now >= time.End;
	}
	public static class Input
	{
		public static bool UseHeld { get; set; }
		public static bool Down( string action ) => action == "Use" && UseHeld;
		public static bool Pressed( string action ) => false;
	}
	public static class GameTask { public static Task DelaySeconds( float delay ) => Task.CompletedTask; }
}
namespace Sandbox.Events
{
	public interface IGameEventHandler<T> { void OnGameEvent( T eventArgs ); }
}
namespace SWB.Base
{
	public class WeaponSettings
	{
		public static WeaponSettings Instance { get; set; }
		public bool AutoReload { get; set; } = true;
	}
}
namespace Facepunch
{
	public interface IDroppedWeaponState<T>;
	public enum WeaponCategory { None, AssaultRifle, SMG, Marksman, Sniper, LMG, Shotgun, Pistol, Launcher }
	public class EquipmentResource { public WeaponCategory Category { get; set; } }
	public class Client { public bool IsBot { get; set; } }
	public class PlayerPawn : Component
	{
		public bool IsLocallyControlled { get; set; } = true;
		public bool IsFrozen { get; set; }
		public bool IsPipeClimbing { get; set; }
		public float TrainingReloadTimeScale { get; set; } = 1f;
		public Client Client { get; } = new();
		public ModelRenderer BodyRenderer { get; set; }
	}
	public class ModelRenderer { public void SetBool( string name, bool value ) { } }
	public class ViewModel { public ModelRenderer ModelRenderer { get; } = new(); }
	public class Magazine
	{
		public float ReloadTime { get; set; }
		public float EmptyReloadTime { get; set; }
		public Dictionary<float, SoundEvent> ReloadSounds { get; set; }
		public Dictionary<float, SoundEvent> EmptyReloadSounds { get; set; }
	}
	public class Equipment : Component
	{
		public PlayerPawn Owner { get; set; } = new();
		public bool IsDeployed { get; set; } = true;
		public TagSet Tags { get; } = new();
		public float AttachmentReloadMultiplier { get; set; } = 1f;
		public int AttachmentMagazineCapacity { get; set; }
		public EquipmentResource Resource { get; set; }
		public Magazine ReloadMagazine { get; set; }
		public ViewModel ViewModel { get; set; }
		public T GetComponentInChildren<T>() where T : class => null;
	}
	public class TagSet : HashSet<string> { public bool Has( string tag ) => Contains( tag ); }
	public class Shootable { public void PlayReloadSmoke() { } }
	public abstract class WeaponInputAction : Component
	{
		protected Equipment Equipment { get; set; } = new();
		protected PlayerPawn Player => Equipment.Owner;
		protected void BindTag( string name, Func<bool> value ) { }
		protected virtual void OnEnabled() { }
		protected virtual void OnUpdate() { }
		protected virtual void OnInput() { }
	}
	public record EquipmentHolsteredEvent( Equipment Equipment );
	public static class ZombiesPlayerState { public static float ReloadScale( PlayerPawn player ) => 1f; }
	public class TestReloadable : Reloadable
	{
		public Equipment Weapon => Equipment;
		public void Tick() => OnUpdate();
		public void ManualReload() => OnInput();
	}
}
