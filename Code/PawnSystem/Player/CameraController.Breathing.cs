namespace Facepunch;

public sealed partial class CameraController
{
	private AimBreathingRules.State _aimBreathing;
	private BreathControlRules.State _breathControl;

	/// <summary>The current breathing offset, shared by the view, sights and unspread firing ray.</summary>
	public Angles AimBreathingOffset { get; private set; }

	private void ApplyAimBreathing()
	{
		if ( !Player.IsValid() || !Player.IsLocallyControlled || !IsActive || Mode != CameraMode.FirstPerson
			|| !Player.HealthComponent.IsValid() || Player.HealthComponent.State != LifeState.Alive
			|| Player.IsFrozen || Player.IsPilotingDrone || Player.IsNoclipping )
		{
			_aimBreathing = default;
			// Changing camera mode must not refill the breath reserve. Death starts a new life.
			_breathControl = !Player.IsValid() || (Player.HealthComponent.IsValid() && Player.HealthComponent.State != LifeState.Alive)
				? default : BreathControlRules.Step( _breathControl, Time.Delta, false, Input.Down( "BreathControl", false ), 0f ).State;
			AimBreathingOffset = Angles.Zero;
			return;
		}

		var equipment = Player.CurrentEquipment;
		var aiming = equipment.IsValid() && equipment.IsDeployed && equipment.HasTag( "aiming" )
			&& !equipment.HasTag( "lowered" ) && !Player.IsMantling && !Player.IsPipeClimbing
			&& equipment.GetComponentInChildren<Shootable>().IsValid()
			&& equipment.GetComponentInChildren<Reloadable>()?.IsReloading != true;
		var fraction = aiming ? (equipment.ViewModel.IsValid() ? equipment.ViewModel.AimProgress : 1f) : 0f;
		var inputBlocked = Input.Suppressed || Input.MouseCursorVisible || GameUtils.IsGunsmithStudioOpen()
			|| UI.ClassSelect.IsAnyOpen || UI.TacticalBuyMenu.IsAnyOpen || UI.ZombiesWorkbenchPanel.IsAnyOpen;
		var canSteady = aiming && fraction >= 0.95f && !inputBlocked && Player.IsGrounded && !Player.IsSprinting
			&& !Player.IsSliding && !Player.IsGettingUp && Player.WishMove.LengthSquared <= 0.01f
			&& Player.CharacterController.IsValid() && Player.CharacterController.Velocity.Length <= 10f;
		var breath = BreathControlRules.Step( _breathControl, Time.Delta, canSteady, Input.Down( "BreathControl", false ), Player.SprintStamina );
		_breathControl = breath.State;
		var sample = AimBreathingRules.Step( _aimBreathing, Time.Delta, fraction, Player.SprintStamina, Player.HandlingXP,
			Player.IsCrouching, Player.IsProne, Player.IsWeaponMounted );
		_aimBreathing = sample.State;
		AimBreathingOffset = new Angles( sample.Pitch * breath.SwayScale, sample.Yaw * breath.SwayScale, 0f );

		// UpdateFromEyes clears local rotation every frame. Apply an absolute offset, never accumulated input:
		// leaving ADS or respawning cannot pull the player's mouse aim away. AimRay reads this camera rotation,
		// and scopes/viewmodels inherit it, so the visible aim and bullets stay together.
		Camera.LocalRotation *= Rotation.From( AimBreathingOffset );
	}
}
