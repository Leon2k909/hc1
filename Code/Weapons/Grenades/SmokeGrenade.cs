namespace Facepunch;

[Title( "Smoke Grenade" )]
public partial class SmokeGrenade : BaseGrenade
{
	[Property] public GameObject FuseEffect { get; set; }
	[Property] public float FuseEffectDelay { get; set; } = 1.5f;
	[Property] public float ExtinguishRadius { get; set; } = 128f;
	/// <summary>Keep the canister through the 70-second burn and the last particles' 13-second fade.</summary>
	[Property] public float SpentCanisterLifetime { get; set; } = 86f;
	
	private TimeUntil FuseEffectStartTime { get; set; }
	private bool Ignited;
	private TimeSince TimeSinceIgnited;
	private GameObject SmokeEffect;
	// Keep the particle collision sphere clear of the floor even when the canister lands on its side or cap.
	private Vector3 VentPosition => WorldTransform.PointToWorld( Vector3.Up * 5.5f ) + Vector3.Up * 2.5f;

	protected override void OnStart()
	{
		WorldWind.Ensure( Scene );
		FuseEffectStartTime = FuseEffectDelay;
		base.OnStart();
	}

	protected override void OnUpdate()
	{
		if ( FuseEffectStartTime && FuseEffect.IsValid() && !FuseEffect.Enabled )
		{
			FuseEffect.Enabled = true;
		}
		
		base.OnUpdate();

		if ( !Ignited ) return;
		if ( SmokeEffect.IsValid() )
		{
			// Only the source follows the canister; emitted particles remain in world space.
			SmokeEffect.WorldPosition = VentPosition;
			SmokeEffect.WorldRotation = Rotation.Identity;
		}
		if ( !IsProxy && TimeSinceIgnited > SpentCanisterLifetime ) GameObject.Destroy();
	}

	protected override bool CanExplode() => !Ignited;

	protected override void Explode()
	{
		Ignite( Game.Random.Int( 1, 65535 ) );
	}

	[Rpc.Broadcast]
	private void Ignite( int seed )
	{
		if ( Ignited ) return;
		Ignited = true;
		TimeSinceIgnited = 0;
		if ( PrefabOnExplode.IsValid() )
		{
			SmokeEffect = PrefabOnExplode.Clone( VentPosition );
			var simulation = SmokeEffect.GetComponent<SmokeSimulation>();
			if ( simulation.IsValid() ) simulation.Seed = seed;
		}

		var radius = ExtinguishRadius * ExtinguishRadius;

		foreach ( var node in MolotovFireNode.All )
		{
			if ( node.WorldPosition.DistanceSquared( WorldPosition ) <= radius )
			{
				node.Extinguish();
			}
		}
	}

	protected override void OnDestroy()
	{
		if ( SmokeEffect.IsValid() ) SmokeEffect.Destroy();
		base.OnDestroy();
	}
}
