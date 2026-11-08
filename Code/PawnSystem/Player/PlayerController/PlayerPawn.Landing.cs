namespace Facepunch;

public partial class PlayerPawn
{
	/// <summary>Vertical closing speed at the boots, before the movement solver removed the impact.</summary>
	internal float LandingImpactSpeed()
	{
		var ground = CharacterController.GroundCollider;
		// Point velocity includes a rigid surface's rotation as well as its translation.
		var surfaceVelocity = ground.IsValid() ? ground.GetVelocityAtPoint( WorldPosition ).z : 0f;
		return LandingImpactRules.ClosingSpeed( _previousVelocity.z, surfaceVelocity );
	}
}
