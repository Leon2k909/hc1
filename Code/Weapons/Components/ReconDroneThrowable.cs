namespace Facepunch;

/// <summary>Uses the normal held/ready/release animation, with a host-owned flying payload.</summary>
public sealed class ReconDroneThrowable : Throwable
{
	protected override bool SpawnOnHost => true;
	protected override bool PlayGrenadeRadio => false;

	protected override void SpawnProjectile( PlayerPawn player )
	{
		var drone = CreateDrone( player );
		if ( drone.IsValid() ) drone.GameObject.NetworkSpawn();
	}

	/// <summary>Prepare the aircraft before publishing its initialized state to the network.</summary>
	public ReconDroneFlight CreateDrone( PlayerPawn player )
	{
		// A remote player's camera is not the host's camera. Use their replicated eye pose.
		var forward = player.EyeAngles.ToRotation().Forward;
		var origin = player.EyePosition;
		var release = origin + forward * 28f + player.EyeAngles.ToRotation().Right * 8f;
		var trace = Scene.Trace.Ray( origin, release ).Radius( 5f )
			.IgnoreGameObjectHierarchy( player.GameObject ).WithoutTags( "trigger" ).Run();
		if ( trace.Hit ) release = trace.EndPosition + trace.Normal * 6f;

		var launched = Prefab.Clone( new CloneConfig
		{
			StartEnabled = false,
			Transform = new Transform( release, Rotation.LookAt( forward, Vector3.Up ) )
		} );
		var drone = launched.GetComponent<ReconDroneFlight>( true );
		var inheritedVelocity = player.IsLocallyControlled && player.CharacterController.IsValid()
			? player.CharacterController.Velocity : player.SyncedVelocity;
		drone.Initialize( player, forward * ThrowPower + Vector3.Up * 100f + inheritedVelocity );
		launched.Flags |= GameObjectFlags.NotSaved;
		launched.Enabled = true;
		return drone;
	}
}
