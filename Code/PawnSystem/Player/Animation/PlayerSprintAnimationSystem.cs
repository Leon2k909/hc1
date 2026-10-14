namespace Facepunch;

/// <summary>Finish the sprint carry after animation, on owners and remote players alike.</summary>
public sealed class PlayerSprintAnimationSystem : GameObjectSystem<PlayerSprintAnimationSystem>
{
	public PlayerSprintAnimationSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, -190, ApplySprintPoses, "PlayerSprintAnimation" );
	}

	private void ApplySprintPoses()
	{
		foreach ( var body in Scene.GetAllComponents<PlayerBody>() )
			if ( body.IsValid() && body.Active ) body.ApplySprintPose();
	}
}
