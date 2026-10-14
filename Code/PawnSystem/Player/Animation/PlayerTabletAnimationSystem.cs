namespace Facepunch;

/// <summary>Keep the held controller visible and gripped on the operator and on remote player bodies.</summary>
public sealed class PlayerTabletAnimationSystem : GameObjectSystem<PlayerTabletAnimationSystem>
{
	public PlayerTabletAnimationSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, -150, ApplyTablets, "PlayerTabletAnimation" );
	}

	private void ApplyTablets()
	{
		foreach ( var body in Scene.GetAllComponents<PlayerBody>() )
			if ( body.IsValid() && body.Active ) body.ApplyTabletPose();
	}
}
