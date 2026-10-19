namespace Facepunch;

/// <summary>
/// Finish the third-person slide and the prone pose after animation and bone merging, on owners and proxies alike.
/// The two never overlap: a slide doesn't run lying down.
/// </summary>
public sealed class PlayerSlideAnimationSystem : GameObjectSystem<PlayerSlideAnimationSystem>
{
	public PlayerSlideAnimationSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, -200, ApplySlides, "PlayerSlideAnimation" );
	}

	private void ApplySlides()
	{
		foreach ( var body in Scene.GetAllComponents<PlayerBody>() )
			if ( body.IsValid() && body.Active )
			{
				body.ApplyPronePose();
				body.ApplySlidePose();
			}
	}
}
