namespace Facepunch;

public enum IdleType
{
	Default,
	WithRifle,
	WithKnife,
	WithPistol,
	Sitting,
	Leaning
}

public sealed class IdleAnimator : Component
{
	[Property] public SkinnedModelRenderer Renderer { get; set; }
	[Property] public GameObject WeaponPrefab { get; set; }
	[Property] public GameObject HoldObject { get; set; }
	[Property] public IdleType IdleType { get; set; }

	/// <summary>
	/// Remove this whole fucking function. Jesus.
	/// </summary>
	/// <param name="eq"></param>
	async void AsyncOn( Equipment eq )
	{
		await GameTask.DelaySeconds( 0.05f );

		if ( !eq.IsValid() )
			return;

		eq.UpdateRenderMode( true );
	}

	protected override void OnStart()
	{
		if ( Renderer.IsValid() && MilitaryUniform.IsLegacyModel( Renderer.Model ) )
			MilitaryUniform.SetModel( Renderer, Renderer.Model );

		var inst = WeaponPrefab?.Clone( new CloneConfig()
		{
			StartEnabled = true,
			Parent = HoldObject,
			Transform = new Transform(),
		} );
		var eq = inst.GetComponentInChildren<Equipment>();
		AsyncOn( eq );
	}

	protected override void OnFixedUpdate()
	{
		if ( Renderer.IsValid() )
		{
			Renderer.Set( "idle_type", (int)IdleType );
			if ( MilitaryUniform.UsesHumanSkeleton( Renderer.Model ) )
			{
				Renderer.Set( "b_grounded", true );
				Renderer.Set( "holdtype", IdleType == IdleType.WithRifle ? 2 : IdleType == IdleType.WithPistol ? 1 : 0 );
			}
		}
	}
}
