namespace Facepunch;

public partial class ViewModel
{
	private readonly WeaponInspectAnimation _inspectAnimation = new();
	private TimeSince _timeSinceInspectDeploy = 0f;
	[Property, Range( 0, 1 ), Group( "Configuration" )] public float InspectPoseScale { get; set; } = 1f;
	[Property, Range( 0, 1 ), Group( "Configuration" )] public float InspectRotationScale { get; set; } = 1f;

	public bool IsInspecting => _inspectAnimation.IsActive;

	protected override void OnEnabled()
	{
		_timeSinceInspectDeploy = 0f;
		_inspectAnimation.Reset();
	}

	protected override void OnDisabled()
	{
		_inspectAnimation.Reset();
	}

	private void UpdateInspect()
	{
		if ( !Equipment.IsValid() || !Owner.IsValid() || !ModelRenderer.IsValid()
			|| !Owner.IsLocallyControlled || !Owner.IsViewer || !Equipment.IsDeployed
			|| Owner.CurrentEquipment != Equipment || Owner.CameraController?.Mode != CameraMode.FirstPerson )
		{
			_inspectAnimation.Reset();
			return;
		}

		var inspectable = !IsThrowable && (Equipment.GetComponentInChildren<Shootable>().IsValid()
			|| Equipment.GetComponentInChildren<Melee>().IsValid());
		var blocked = !inspectable || _timeSinceInspectDeploy < 0.5f || Owner.IsFrozen
			|| Input.Suppressed || Input.EscapePressed || !GameUtils.ShouldHideCombatMouse( Owner )
			|| Equipment.HasTag( "aiming" ) || Equipment.HasTag( "scoped" )
			|| Equipment.HasTag( "reloading" ) || Equipment.HasTag( "lowered" ) || Equipment.HasTag( "no_shooting" )
			|| Owner.IsSprinting || Input.Down( "attack1" ) || Input.Down( "attack2" )
			|| Input.Down( "reload" ) || Input.Down( "use" )
			|| (Input.Down( "Run" ) && Owner.WishMove.Length > 0f);

		_inspectAnimation.Update( Input.Pressed( WeaponInspectAnimation.InputAction ), blocked, Time.Delta, InspectPoseScale, InspectRotationScale );
	}

	private void ApplyInspectPose()
	{
		var pose = _inspectAnimation.Pose;
		WorldPosition += WorldRotation * pose.Position;
		WorldRotation *= pose.Rotation;
	}
}
