global using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System.Text.Json;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
void Close( float actual, float expected, string message ) => Check( MathF.Abs( actual - expected ) < 0.00001f, message );
foreach ( var patterned in new[] { false, true } )
foreach ( var delta in new[] { 1f / 30f, 1f / 50f, 1f / 144f } )
{
	Time.Delta = delta;
	var gun = new ShootRecoil
	{
		UseRecoilPattern = patterned, Scale = new( 1, 1 ),
		VerticalSpread = new( 5f ), HorizontalSpread = new( 2f )
	};
	var player = gun.Player;
	foreach ( var stance in new[] { "standing", "crouched", "prone", "mounted", "all", "airborne", "sliding", "rising" } )
	{
		player.IsCrouching = stance is "crouched" or "all" or "airborne" or "sliding" or "rising";
		player.IsProne = stance is "prone" or "all";
		player.IsWeaponMounted = stance is "mounted" or "all";
		player.IsGrounded = stance != "airborne";
		player.IsSliding = stance == "sliding";
		player.IsGettingUp = stance == "rising";
		var support = stance switch { "crouched" => 0.85f, "prone" => 0.7f, "mounted" or "all" => 0.55f, _ => 1f };
		gun.ClearRecoil();
		gun.Shoot();
		Close( gun.Current.pitch, -5f * 0.02f * support, $"{patterned}/{delta}/{stance}: vertical recoil must use the strongest valid support." );
		Close( MathF.Abs( gun.Current.yaw ), 2f * 0.02f * support, $"{patterned}/{delta}/{stance}: horizontal recoil must use the same support." );
	}
	player.IsGettingUp = false;
	player.IsCrouching = true;
	player.TrainingRecoilScale = 0.88f;
	player.HealthComponent.WoundRecoilScale = 1.25f;
	GunsmithAttachmentEffects.Current = new() { VerticalRecoil = 0.9f, HorizontalRecoil = 1.1f };
	gun.ClearRecoil();
	gun.Shoot();
	var scale = 0.85f * 0.88f * 1.25f;
	Close( gun.Current.pitch, -5f * 0.02f * scale * 0.9f, "Training, wounds and vertical attachments must compose with support." );
	Close( MathF.Abs( gun.Current.yaw ), 2f * 0.02f * scale * 1.1f, "Horizontal attachments must remain independent." );
	var first = gun.Current.pitch;
	gun.Shoot();
	Close( gun.Current.pitch, first * 2f, "Every discharge must add its own impulse." );
	gun.ClearRecoil();
	Close( gun.Current.pitch, 0f, "Clearing recoil must reset accumulated impulse." );
	GunsmithAttachmentEffects.Current = new();
}

foreach ( var patterned in new[] { false, true } )
{
	var gun = new ShootRecoil { UseRecoilPattern = patterned, Scale = new( 1, 1 ), VerticalSpread = new( 5f ) };
	gun.Weapon.LoadedMass = 3.4f;
	gun.Weapon.Resource = new() { ResourcePath = "weapons/m4a1/m4a1.equip" };
	gun.Weapon.Bullet = new() { AmmoComponent = new() { Ammo = 29, Capacity = 30 } };
	gun.Shoot();
	Close( gun.Current.pitch, -0.1f, "First shot must retain full-mag recoil after Shootable decrements ammo." );
	gun.Weapon.Bullet.AmmoComponent.Ammo = 0;
	gun.ClearRecoil();
	gun.Shoot();
	Close( gun.Current.pitch, -0.1f * 3.4f / (3.4f - 29f * 0.0123f), "Last shot must use the mass of the one remaining live cartridge." );
	gun.Weapon.Bullet.AmmoComponent.Ammo = 29;
	gun.ClearRecoil();
	gun.Shoot();
	Close( gun.Current.pitch, -0.1f, "A reload must immediately restore the authored full-mag recoil." );
	gun.Weapon.Bullet.AmmoComponent.Ammo = 0;
	GunsmithAttachmentEffects.Current = new() { LoadedMass = 4f };
	gun.ClearRecoil();
	gun.Shoot();
	Close( gun.Current.pitch, -0.1f * 4f / (4f - 29f * 0.0123f), "The depletion adjustment must use the fitted gun's full mass." );
	GunsmithAttachmentEffects.Current = new();
}

var root = args[0];
using var input = JsonDocument.Parse( File.ReadAllText( Path.Combine( root, "ProjectSettings/Input.config" ) ) );
var breathActions = input.RootElement.GetProperty( "Actions" ).EnumerateArray()
	.Where( x => x.GetProperty( "Name" ).GetString() == "BreathControl" ).ToArray();
Check( breathActions.Length == 1, "Breath control must have exactly one configurable action." );
Check( breathActions[0].GetProperty( "KeyboardCode" ).GetString() == "None"
	&& breathActions[0].GetProperty( "GamepadCode" ).GetString() == "None", "Breath control must be unbound on keyboard and controller by default." );
var camera = File.ReadAllText( Path.Combine( root, "Code/PawnSystem/Player/CameraController.Breathing.cs" ) );
Check( !camera.Contains( "Input.Down( \"Run\"" ) && camera.Contains( "Input.Down( \"BreathControl\", false )" ),
	"Breath control must read its own action and never the sprint binding." );
Console.WriteLine( $"PASS: {checks} production recoil and default-binding checks." );

// Deterministic engine seams; the complete ShootRecoil component is linked from production.
namespace Sandbox
{
	public static class Validity { public static bool IsValid( this object value ) => value is not null; }
	public class PropertyAttribute : Attribute;
	public class TitleAttribute( string name ) : Attribute;
	public class GroupAttribute( string name ) : Attribute;
	public class CategoryAttribute( string name ) : Attribute;
	public class FeatureAttribute( string name ) : Attribute;
	public class FeatureEnabledAttribute( string name ) : Attribute;
	public static class Time { public static float Delta; }
	public readonly record struct TimeSince( float Value )
	{
		public static implicit operator TimeSince( float value ) => new( value );
		public static bool operator >( TimeSince time, float value ) => time.Value > value;
		public static bool operator <( TimeSince time, float value ) => time.Value < value;
	}
	public readonly record struct Vector2( float x, float y );
	public readonly record struct RangedFloat( float Value ) { public float GetValue() => Value; }
	public readonly record struct Angles( float pitch, float yaw, float roll )
	{
		public static Angles Zero => default;
		public static Angles operator +( Angles a, Angles b ) => new( a.pitch + b.pitch, a.yaw + b.yaw, a.roll + b.roll );
		public static Angles operator *( Angles a, float scale ) => new( a.pitch * scale, a.yaw * scale, a.roll * scale );
		public Angles LerpTo( Angles target, float t ) => this * (1f - t) + target * t;
	}
}
namespace Facepunch
{
	public class EquipmentComponent
	{
		public PlayerPawn Player { get; } = new();
		protected Equipment Equipment { get; } = new();
		protected virtual void OnUpdate() { }
	}
	public class PlayerPawn
	{
		public bool IsWeaponMounted, IsProne, IsCrouching, IsSliding, IsGettingUp;
		public bool IsGrounded = true, IsLocallyControlled = true;
		public float TrainingRecoilScale = 1f;
		public Health HealthComponent { get; } = new();
		public bool IsValid() => true;
	}
	public class Health { public float WoundRecoilScale = 1f; }
	public partial class ShootRecoil { public Equipment Weapon => Equipment; }
	public class Equipment
	{
		public float LoadedMass;
		public EquipmentResource Resource;
		public Shootable Bullet;
		public T GetComponentInChildren<T>() where T : class => Bullet as T;
	}
	public class EquipmentResource { public string ResourcePath; }
	public class Shootable { public WeaponAmmo AmmoComponent; }
	public class WeaponAmmo
	{
		public int Ammo, Capacity;
		public bool HasChamber = true;
		public int GetEffectiveMaxAmmo() => Capacity;
	}
	public struct RecoilPattern { public Vector2 GetPoint( ref int frame ) => new( 2f, 5f ); }
}
namespace Facepunch.Gunsmith
{
	public class GunsmithAttachmentEffects
	{
		public float VerticalRecoil = 1f, HorizontalRecoil = 1f;
		public float LoadedMass;
		public static GunsmithAttachmentEffects Current = new();
		public static GunsmithAttachmentEffects For( object equipment ) => Current;
	}
}
