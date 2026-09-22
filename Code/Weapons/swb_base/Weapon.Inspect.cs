namespace SWB.Base;

public partial class Weapon
{
	private readonly Facepunch.WeaponInspectAnimation inspectAnimation = new();
	public Transform InspectPose => inspectAnimation.Pose;

	private void UpdateInspectAnimation()
	{
		if ( IsProxy || Owner is null || Owner.IsBot ) return;

		if ( !Owner.IsAlive || !Owner.IsFirstPerson )
		{
			inspectAnimation.Reset();
			IsInspecting = false;
			return;
		}

		var blocked = IsDeploying || IsScoping || IsAiming || IsReloading || IsRunning
			|| IsCustomizing || InBoltBack || ShouldTuckVar || IsShooting()
			|| Input.Suppressed || Input.EscapePressed || !Facepunch.GameUtils.ShouldHideCombatMouse()
			|| Input.Down( "attack1" ) || Input.Down( "attack2" ) || Input.Down( "reload" )
			|| Input.Down( "use" ) || (Input.Down( "Run" ) && Owner.Velocity.Length > 10f);

		inspectAnimation.Update( Input.Pressed( Facepunch.WeaponInspectAnimation.InputAction ), blocked, Time.Delta );
		IsInspecting = inspectAnimation.IsActive;
	}
}
