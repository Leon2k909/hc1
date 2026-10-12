namespace Facepunch;

/// <summary>
/// A recon ground station. The first press sets the octocopter down or releases the nano drone from the operator's
/// hand, then opens its feed; after that, a press takes control of it again. One drone a station: when the
/// drone is lost or lands flat, the station goes too (<see cref="ReconOctocopter"/>).
/// </summary>
public sealed class ReconTabletLink : WeaponInputAction
{
	[Property] public GameObject Prefab { get; set; }

	/// <summary>How far ahead of the operator it's set down: its rotors are 1.5 m across.</summary>
	[Property] public float LaunchDistance { get; set; } = 70f;
	[Property] public bool HandLaunch { get; set; }

	/// <summary>Since a launch was refused for lack of room, for the HUD.</summary>
	public static TimeSince SinceRefused { get; private set; } = 10f;

	/// <summary>The drone this station flies, on the operator's machine.</summary>
	public static ReconOctocopter OwnDrone( PlayerPawn player, string stationResourcePath = null )
	{
		if ( !player.IsValid() ) return null;
		return player.Scene.GetAllComponents<ReconOctocopter>().FirstOrDefault( d => !d.IsProxy && d.Operator == player
			&& (stationResourcePath is null || string.Equals( d.StationResourcePath, stationResourcePath, StringComparison.OrdinalIgnoreCase ))
			&& !d.IsDestroyed && d.State is not (ReconOctocopter.FlightState.Falling or ReconOctocopter.FlightState.Wreck) );
	}

	protected override void OnInputDown()
	{
		var player = Player;
		if ( !player.IsValid() || ReconOctocopter.IsPiloting( player ) || ReconOctocopter.JustUnlinked ) return;
		if ( player.HealthComponent.State != LifeState.Alive ) return;

		var drone = OwnDrone( player, player.CurrentEquipment?.Resource?.ResourcePath );
		if ( drone.IsValid() )
		{
			if ( !drone.IsHandReleasing ) drone.Link();
			return;
		}
		Launch( player );
	}

	private void Launch( PlayerPawn player )
	{
		if ( Prefab is null ) return;
		if ( HandLaunch )
		{
			LaunchFromHand( player );
			return;
		}
		var heading = Rotation.FromYaw( player.EyeAngles.yaw );
		var chest = player.WorldPosition + Vector3.Up * 40f;

		// Out in front, as far as the way is clear.
		var reach = Scene.Trace.Ray( chest, chest + heading.Forward * LaunchDistance ).Radius( 8f )
			.IgnoreGameObjectHierarchy( player.GameObject )
			.WithoutTags( "trigger", "ragdoll", "playerclip" )
			.Run();
		var distance = reach.Hit ? reach.Distance - 32f : LaunchDistance;
		if ( distance < 36f )
		{
			Refuse();
			return;
		}

		// Set down on something level.
		var above = chest + heading.Forward * distance;
		var ground = Scene.Trace.Ray( above, above + Vector3.Down * 120f )
			.IgnoreGameObjectHierarchy( player.GameObject )
			.WithoutTags( "trigger", "ragdoll", "playerclip", "player", "movement" )
			.Run();
		if ( !ground.Hit || ground.Normal.z < 0.7f )
		{
			Refuse();
			return;
		}

		var spawned = Prefab.Clone( new CloneConfig
		{
			StartEnabled = false,
			Transform = new Transform( ground.EndPosition, heading )
		} );
		var drone = spawned.GetComponent<ReconOctocopter>( true );
		if ( !drone.IsValid() )
		{
			spawned.Destroy();
			return;
		}

		// Stood on its skids, with room over its rotors to climb.
		var origin = ground.EndPosition + Vector3.Up * (0.5f - drone.Hull.Mins.z);
		var room = Scene.Trace.Box( drone.Hull, origin + Vector3.Up * 2f, origin + Vector3.Up * 100f )
			.IgnoreGameObjectHierarchy( player.GameObject )
			.WithoutTags( "trigger", "ragdoll", "playerclip", "player", "movement" )
			.Run();
		if ( room.StartedSolid || room.Hit && room.Distance < 60f )
		{
			spawned.Destroy();
			Refuse();
			return;
		}

		spawned.WorldPosition = origin;
		spawned.Flags |= GameObjectFlags.NotSaved;
		drone.Initialize( player );
		spawned.Enabled = true;
		spawned.NetworkSpawn();
	}

	private void LaunchFromHand( PlayerPawn player )
	{
		// Use the replicated eye height, so crouching and prone don't spawn it over the head.
		var heading = Rotation.FromYaw( player.EyeAngles.yaw );
		var aim = player.EyeAngles.ToRotation();
		var hand = ReconFlightMath.HandReleasePoint( player.EyePosition, aim, 0f );
		var origin = ReconFlightMath.HandReleasePoint( player.EyePosition, aim, LaunchDistance );
		var spawned = Prefab.Clone( new CloneConfig
		{
			StartEnabled = false,
			Transform = new Transform( origin, heading )
		} );
		var drone = spawned.GetComponent<ReconOctocopter>( true );
		if ( !drone.IsValid() ) { spawned.Destroy(); return; }
		var hull = drone.CollisionHullFor( heading );
		var reach = Scene.Trace.Box( hull, hand, origin )
			.IgnoreGameObjectHierarchy( player.GameObject ).IgnoreGameObjectHierarchy( spawned )
			.WithoutTags( "trigger", "ragdoll" ).Run();
		var room = Scene.Trace.Box( hull, origin, origin + Vector3.Up * 10f )
			.IgnoreGameObjectHierarchy( player.GameObject ).IgnoreGameObjectHierarchy( spawned )
			.WithoutTags( "trigger", "ragdoll" ).Run();
		if ( reach.StartedSolid || reach.Hit || room.StartedSolid || room.Hit )
		{
			spawned.Destroy();
			Refuse();
			return;
		}
		// It leaves the hand directly; it doesn't need level ground or a large launch pad.
		spawned.Flags |= GameObjectFlags.NotSaved;
		drone.Initialize( player );
		spawned.Enabled = true;
		spawned.NetworkSpawn( player.Network.Owner );
	}

	private static void Refuse()
	{
		SinceRefused = 0;
	}
}
