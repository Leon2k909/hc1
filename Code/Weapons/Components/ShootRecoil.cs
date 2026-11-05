using Facepunch.Gunsmith;

namespace Facepunch;

[Title( "Recoil" ), Group( "Weapon Components" )]
public partial class ShootRecoil : EquipmentComponent
{
	[Property] public float ResetTime { get; set; } = 0.3f;

	// Recoil Patterns
	[Property, FeatureEnabled( "Recoil Pattern" )] public bool UseRecoilPattern { get; set; } = false;
	[Property, Category( "UseRecoilPattern" ), Feature( "Recoil Pattern" )] public Vector2 Scale { get; set; } = new Vector2( 2f, 5f );
	[Property, Category( "UseRecoilPattern" ), Feature( "Recoil Pattern" ) ] public RecoilPattern RecoilPattern { get; set; } = new();
	[Property, Group( "Standard Recoil" ), Feature( "Standard Recoil" )] public RangedFloat HorizontalSpread { get; set; } 
	[Property, Group( "Standard Recoil" ), Feature( "Standard Recoil" )] public RangedFloat VerticalSpread { get; set; }

	internal Angles Current { get; private set; }

	TimeSince TimeSinceLastShot;
	int currentFrame = 0;

	/// <summary>
	/// Recoil scale from tuning. +10 = -15% recoil, -10 = +15% recoil.
	/// Weapon tuning is off (see WeaponTuningManager), so it's 1.
	/// </summary>
	private float GetRecoilScale()
	{
		return 1f;
		// Put back with tuning:
		// var weaponId = Equipment?.Resource?.ResourceName ?? string.Empty;
		// if ( string.IsNullOrEmpty( weaponId ) ) return 1f;
		// var tune = WeaponTuningManager.GetTuning( weaponId );
		// return 1f - tune.Recoil * 0.015f;
	}

	/// <summary>Stance support is a gameplay approximation; use the strongest support without stacking it.</summary>
	private float GetSupportScale()
	{
		if ( Player?.IsWeaponMounted == true ) return 0.55f;
		// A stance flag alone (for example in mid-air or during a slide) does not brace the firearm.
		if ( Player?.IsGrounded != true || Player.IsSliding || Player.IsGettingUp ) return 1f;
		if ( Player.IsProne ) return 0.70f;
		return Player.IsCrouching ? 0.85f : 1f;
	}

	private float GetLoadedAmmoRecoilScale( GunsmithAttachmentEffects attachments )
	{
		if ( !Equipment.IsValid() ) return 1f;
		var shootable = Equipment.GetComponentInChildren<Shootable>();
		var ammo = shootable.IsValid() ? shootable.AmmoComponent : null;
		if ( !ammo.IsValid() ) return 1f;
		var fullMass = attachments.LoadedMass > 0f ? attachments.LoadedMass : Equipment.LoadedMass;
		// Shootable has already consumed this shot's round before dispatching recoil.
		return LoadedAmmoMassRules.RecoilScale( fullMass, LoadedAmmoMassRules.CartridgeKg( Equipment.Resource?.ResourcePath ),
			ammo.GetEffectiveMaxAmmo(), (long)ammo.Ammo + 1L, ammo.HasChamber );
	}

	internal void Shoot()
	{
		if ( TimeSinceLastShot > ResetTime )
			currentFrame = 0;

		TimeSinceLastShot = 0;

		// These recoil values were authored against the 50 Hz simulation tick. A discharge is an
		// impulse, not a force over the current frame: keep its magnitude independent of tick length.
		const float shotScale = 1f / 50f;
		// Hardcore: a shot arm or hand can't hold the gun down as well.
		var recoilScale = GetRecoilScale() * (Player?.HealthComponent?.WoundRecoilScale ?? 1f)
			* GetSupportScale() * (Player?.TrainingRecoilScale ?? 1f);
		var attachments = GunsmithAttachmentEffects.For( Equipment );
		recoilScale *= GetLoadedAmmoRecoilScale( attachments );

		if ( UseRecoilPattern )
		{
			var point = RecoilPattern.GetPoint( ref currentFrame );

			var newAngles = new Angles( -point.y * Scale.y * recoilScale * attachments.VerticalRecoil,
				-point.x * Scale.x * recoilScale * attachments.HorizontalRecoil, 0 ) * shotScale;
			Current = Current + newAngles;
			currentFrame++;
		}
		else
		{
			var newAngles = new Angles( -VerticalSpread.GetValue() * recoilScale * attachments.VerticalRecoil * shotScale,
				HorizontalSpread.GetValue() * recoilScale * attachments.HorizontalRecoil * shotScale, 0 );
			Current = Current + newAngles;
		}

	}

	internal void ClearRecoil()
	{
		Current = Angles.Zero;
		currentFrame = 0;
	}

	protected override void OnUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.IsLocallyControlled )
			return;

		Current = Current.LerpTo( Angles.Zero, Time.Delta * 10f );
	}
}
