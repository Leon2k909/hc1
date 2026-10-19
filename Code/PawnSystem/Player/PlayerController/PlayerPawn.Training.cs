namespace Facepunch;

public partial class PlayerPawn
{
	public int EnduranceXP => Client.IsValid() ? Client.GetTrainingXP( SoldierSkill.Endurance ) : 0;
	public int HandlingXP => Client.IsValid() ? Client.GetTrainingXP( SoldierSkill.Handling ) : 0;
	public float TrainingRecoveryScale => SoldierTrainingRules.RecoveryScale( EnduranceXP );
	public float TrainingRecoilScale => SoldierTrainingRules.RecoilScale( HandlingXP );
	public float TrainingSwayScale => SoldierTrainingRules.SwayScale( HandlingXP );
	public float TrainingAimTimeScale => SoldierTrainingRules.AimTimeScale( HandlingXP );
	public float TrainingReloadTimeScale => SoldierTrainingRules.ReloadTimeScale( HandlingXP );

	[Sync] public float SprintStamina { get; private set; } = 1f;
	[Sync] public bool SprintExhausted { get; private set; }
	private float _sprintRecoveryWait;
	private Vector3 _previousStaminaPosition;
	private bool _hasStaminaPosition;

	private void UpdateSprintStamina()
	{
		if ( !IsLocallyControlled ) return;
		var distance = (WorldPosition - _previousStaminaPosition).WithZ( 0f ).Length;
		var moving = _hasStaminaPosition && distance > 0.01f
			&& distance < Math.Max( GetWishSpeed(), 60f ) * Time.Delta * 2f + 4f;
		_previousStaminaPosition = WorldPosition;
		_hasStaminaPosition = true;
		var running = IsSprinting && moving && IsGrounded && !IsNoclipping && !IsFrozen
			&& !IsProne && !IsCrouching && !IsSliding && !IsMantling && !IsPipeClimbing && !IsPilotingDrone;
		var state = SoldierTrainingRules.StepStamina(
			new( SprintStamina, SprintExhausted, _sprintRecoveryWait ), running, Time.Delta, EnduranceXP );
		SprintStamina = state.Stamina;
		SprintExhausted = state.Exhausted;
		_sprintRecoveryWait = state.RecoveryWait;
	}

	private void ResetSprintStamina()
	{
		SprintStamina = 1f;
		SprintExhausted = false;
		_sprintRecoveryWait = 0f;
		_hasStaminaPosition = false;
		IsSprinting = false;
		WantsToggleSprint = false;
	}
}
