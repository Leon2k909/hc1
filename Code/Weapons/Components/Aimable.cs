namespace Facepunch;

[Title( "ADS (Aim Down Sight)" ), Group( "Weapon Components" )]
public partial class Aimable : WeaponInputAction
{
	[Sync, Change( nameof( OnIsAimingChanged ) )] public bool IsAiming { get; set; }
	private bool WantsToggleAim { get; set; }

	/// <summary>
	/// ADS walk speed multiplier from tuning. +10 = 20% faster ADS walking.
	/// </summary>
	internal float GetAdsMoveScale()
	{
		var weaponId = Equipment?.Resource?.ResourceName ?? string.Empty;
		if ( string.IsNullOrEmpty( weaponId ) ) return 1f;
		var tune = WeaponTuningManager.GetTuning( weaponId );
		return 1f + tune.AdsMoveSpeed * 0.02f;
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
		BindTag( "no_sprint", () => IsAiming || IsDown() );
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
		if ( IsDown() && Equipment.HasTag( "lowered" ) )
		{
			Equipment.SetTag( "lowered", false );
			return false;
		}

		// Self checks first
		if ( Tags.Has( "no_aiming" ) ) return false;
		if ( GameUtils.IsGunsmithStudioOpen() ) return false;
		// if ( Tags.Has( "reloading" ) ) return false;

		if ( !Player.IsValid() )
			return false;

		// Player controller
		if ( !Player.IsGrounded ) return false;
		if ( Player.IsSprinting ) return false;
		if ( Player.Tags.Has( "no_aiming" ) ) return false;

		return true;
	}

	protected override void OnUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.IsLocallyControlled )
			return;

		if ( !CanAim() )
		{
			WantsToggleAim = false;
			IsAiming = false;
			return;
		}

		IsAiming = GameSettingsSystem.Current.ToggleAim ? WantsToggleAim : IsDown();
	}
}
