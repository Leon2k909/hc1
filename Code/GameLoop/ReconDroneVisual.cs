namespace Facepunch;

/// <summary>The visible reconnaissance aircraft accompanying a team's active UAV reward.</summary>
public sealed class ReconDroneVisual : Component
{
	[Property] public GameObject Propeller { get; set; }
	[Property, Sync( SyncFlags.FromHost )] public Team ReconTeam { get; set; }
	[Property] public Vector3 OrbitCenter { get; set; }
	[Property] public float OrbitRadius { get; set; } = 1400f;
	[Property] public float OrbitSeconds { get; set; } = 24f;
	private TimeSince FlightTime;
	private TimeUntil Expires;
	private float PropellerAngle;

	protected override void OnStart()
	{
		if ( IsProxy ) return;
		FlightTime = 0;
		Refresh();
		UpdateFlight();
	}

	/// <summary>A repeated reward keeps the same aircraft in the sky.</summary>
	public void Refresh()
	{
		if ( !IsProxy ) Expires = 31f;
	}

	protected override void OnFixedUpdate()
	{
		if ( IsProxy ) return;
		if ( Expires ) { GameObject.Destroy(); return; }
		UpdateFlight();
	}

	private void UpdateFlight()
	{
		var direction = ReconTeam == Team.CounterTerrorist ? 1f : -1f;
		var angle = (float)FlightTime * MathF.Tau / MathF.Max( OrbitSeconds, 1f ) * direction;
		var radial = new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0 );
		WorldPosition = OrbitCenter + radial * OrbitRadius;
		var forward = new Vector3( -radial.y, radial.x, 0 ) * direction;
		WorldRotation = Rotation.LookAt( forward, Vector3.Up ) * Rotation.FromRoll( -direction * 12f );
	}

	protected override void OnUpdate()
	{
		if ( !Propeller.IsValid() ) return;
		PropellerAngle = (PropellerAngle + Time.Delta * 2400f) % 360f;
		Propeller.LocalRotation = Rotation.FromRoll( PropellerAngle );
	}

	public static ReconDroneVisual Spawn( Scene scene, Team team )
	{
		if ( !Networking.IsHost ) return null;
		using var scope = scene.Push();
		var positions = scene.GetAllComponents<PlayerPawn>().Select( p => p.WorldPosition ).ToArray();
		var centre = positions.Length == 0 ? Vector3.Zero : positions.Aggregate( Vector3.Zero, (sum, p) => sum + p ) / positions.Length;
		centre.z = (positions.Length == 0 ? 0 : positions.Max( p => p.z )) + 1800f;
		var go = GameObject.Clone( "prefabs/scorestreaks/recon_drone.prefab", new CloneConfig
		{
			StartEnabled = false,
			Transform = new Transform( centre + Vector3.Forward * 1400f )
		} );
		if ( !go.IsValid() ) return null;
		go.Flags |= GameObjectFlags.NotSaved;
		var drone = go.GetComponent<ReconDroneVisual>( true );
		drone.ReconTeam = team;
		drone.OrbitCenter = centre;
		go.Enabled = true;
		go.NetworkSpawn();
		return drone;
	}
}
