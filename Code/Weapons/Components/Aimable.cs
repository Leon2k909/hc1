namespace Facepunch;

[Title( "ADS (Aim Down Sight)" ), Group( "Weapon Components" )]
public partial class Aimable : WeaponInputAction
{
	[Sync, Change( nameof( OnIsAimingChanged ) )] public bool IsAiming { get; set; }
	private bool WantsToggleAim { get; set; }

	/// <summary>
	/// ADS walk speed multiplier from tuning. +10 = 20% faster ADS walking.
	/// Weapon tuning is off (see WeaponTuningManager), so it's 1.
	/// </summary>
	internal float GetAdsMoveScale()
	{
		return 1f;
		// Put back with tuning:
		// var weaponId = Equipment?.Resource?.ResourceName ?? string.Empty;
		// if ( string.IsNullOrEmpty( weaponId ) ) return 1f;
		// var tune = WeaponTuningManager.GetTuning( weaponId );
		// return 1f + tune.AdsMoveSpeed * 0.02f;
	}

	protected void OnIsAimingChanged( bool before, bool after )
	{
		if ( !Equipment.IsValid() )
			return;

		if ( after )
		{
			Equipment.SetTag( "aiming", true );
		}
		else
		{
			Equipment.SetTag( "aiming", false );
		}
	}

	protected override void OnEnabled()
	{
		// Sprinting is allowed while aimed in.
	}

	protected override void OnDisabled()
	{
		CancelAim();
	}

	public void CancelAim()
	{
		WantsToggleAim = false;
		IsAiming = false;
	}

	/// <summary>
	/// Aim held through a weapon switch aims the gun switched to. In toggle mode a press held through it would toggle
	/// the new gun's aim, so that waits for a new press.
	/// </summary>
	protected override bool TakesInputHeldThroughDeploy => !GameSettingsSystem.Current.ToggleAim;

	protected override void OnInputDown()
	{
		if ( GameSettingsSystem.Current.ToggleAim )
		{
			WantsToggleAim = !WantsToggleAim;
		}
	}

	protected override void OnInputUp()
	{
		if ( !GameSettingsSystem.Current.ToggleAim )
		{
			WantsToggleAim = false;
		}
	}

	protected virtual bool CanAim()
	{
		if ( Player.IsValid() && Player.IsPipeClimbing ) return false;
		if ( IsDown() && Equipment.HasTag( "lowered" ) )
		{
			Equipment.SetTag( "lowered", false );
			return false;
		}

		// A short no_aiming lockout (for example, just after leaving the ground) should
		// prevent starting ADS, but must not cancel an aim that's already held.
		// Otherwise jumping briefly drops the weapon out of the sights.
		if ( !IsAiming && Tags.Has( "no_aiming" ) ) return false;
		if ( GameUtils.IsGunsmithStudioOpen() ) return false;
		// if ( Tags.Has( "reloading" ) ) return false;

		if ( !Player.IsValid() )
			return false;

		// Player controller
		if ( !IsAiming && Player.Tags.Has( "no_aiming" ) ) return false;

		return true;
	}

	protected override void OnUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.IsLocallyControlled )
			return;

		// Holstering cancelled the aim, and a holstered gun's input is left as it was when it went away.
		if ( !Equipment.IsValid() || !Equipment.IsDeployed )
			return;

		if ( !CanAim() )
		{
			WantsToggleAim = false;
			IsAiming = false;
			return;
		}

		IsAiming = DevCommands.ForceAim || (GameSettingsSystem.Current.ToggleAim ? WantsToggleAim : IsDown());
	}
}
