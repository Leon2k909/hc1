using Sandbox.Events;

namespace Facepunch;

/// <summary>A hand-launched aircraft that climbs, circles, and spots enemies in camera sight.</summary>
public sealed class ReconDroneFlight : Component, ICustomMinimapIcon, IGameEventHandler<ResetScoresEvent>
{
	[Property] public GameObject Propeller { get; set; }
	[Property] public float FlightDuration { get; set; } = 30f;
	[Property] public float ScanRange { get; set; } = 1600f;
	[Sync( SyncFlags.FromHost )] public PlayerPawn Operator { get; private set; }
	[Sync( SyncFlags.FromHost )] public Team ReconTeam { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsScanning { get; private set; }
	[Sync( SyncFlags.FromHost )] private NetList<Guid> Contacts { get; set; } = new();
	private Vector3 velocity;
	private Vector3 orbitCenter;
	private TimeSince flightAge;
	private TimeSince sinceScan;
	private float propellerAngle;

	public void Initialize( PlayerPawn owner, Vector3 launchVelocity )
	{
		Operator = owner;
		ReconTeam = owner.Team;
		velocity = launchVelocity;
		var heading = launchVelocity.WithZ( 0 ).Normal;
		if ( heading.LengthSquared < .1f ) heading = Vector3.Forward;
		orbitCenter = WorldPosition + heading * 450f + Vector3.Up * 400f;
		flightAge = 0;
		sinceScan = 0;
		// Replenished tacticals replace this operator's previous drone, not teammates' drones.
		foreach ( var previous in Scene.GetAllComponents<ReconDroneFlight>().Where( d => d != this && d.Operator == owner ).ToArray() )
			previous.GameObject.Destroy();
	}

	protected override void OnFixedUpdate()
	{
		if ( !Networking.IsHost ) return;
		if ( !Operator.IsValid() || flightAge >= FlightDuration )
		{
			GameObject.Destroy();
			return;
		}
		AdvanceFlight( Time.Delta );
		if ( !IsValid ) return;
		IsScanning = flightAge >= 1.2f;
		if ( IsScanning && sinceScan > .5f )
		{
			sinceScan = 0;
			Scan();
		}
	}

	private void AdvanceFlight( float delta )
	{
		if ( flightAge < .65f )
			velocity += Vector3.Down * 220f * delta;
		else
		{
			var radial = (WorldPosition - orbitCenter).WithZ( 0 );
			var direction = radial.Length > 1f ? radial.Normal : Vector3.Forward;
			var tangent = Vector3.Cross( Vector3.Up, direction );
			var desired = tangent * 520f - direction * ((radial.Length - 340f) * 1.8f).Clamp( -300f, 300f );
			desired.z = ((orbitCenter.z - WorldPosition.z) * 1.8f).Clamp( -160f, 200f );
			velocity = velocity.LerpTo( desired, (delta * 2.5f).Clamp( 0f, 1f ) );
		}

		var next = WorldPosition + velocity * delta;
		var trace = Scene.Trace.Ray( WorldPosition, next ).Radius( 5f )
			.IgnoreGameObjectHierarchy( GameObject ).IgnoreGameObjectHierarchy( Operator.GameObject )
			.WithoutTags( "trigger" ).Run();
		if ( trace.Hit )
		{
			// A blocked launch cannot fly through a ceiling or wall and reveal enemies beyond it.
			GameObject.Destroy();
			return;
		}
		WorldPosition = next;
		if ( velocity.LengthSquared > 1f )
			WorldRotation = Rotation.Lerp( WorldRotation, Rotation.LookAt( velocity.Normal, Vector3.Up )
				* Rotation.FromRoll( flightAge < .65f ? 0f : -12f ), (delta * 7f).Clamp( 0f, 1f ) );
	}

	private bool CanSpot( GameObject target, Team team, Vector3 point )
	{
		if ( target == Operator.GameObject || (!GameUtils.IsFreeForAllMode && team == ReconTeam) ) return false;
		if ( WorldPosition.DistanceSquared( point ) > ScanRange * ScanRange ) return false;
		return !Scene.Trace.Ray( WorldPosition, point ).IgnoreGameObjectHierarchy( GameObject )
			.IgnoreGameObjectHierarchy( target ).WithoutTags( "trigger" ).Run().Hit;
	}

	private void Scan()
	{
		var visible = new HashSet<Guid>();
		foreach ( var pawn in Scene.GetAllComponents<PlayerPawn>() )
		{
			if ( !pawn.HealthComponent.IsValid() || pawn.HealthComponent.State != LifeState.Alive ) continue;
			if ( pawn.GetComponent<PlayerPerks>()?.HasPerk( "ghost" ) == true ) continue;
			if ( CanSpot( pawn.GameObject, pawn.Team, pawn.WorldPosition + Vector3.Up * 40f ) ) visible.Add( pawn.GameObject.Id );
		}
		foreach ( var bot in Scene.GetAllComponents<LightweightCombatBot>() )
			if ( bot.IsAlive && CanSpot( bot.GameObject, bot.Team, bot.WorldPosition + Vector3.Up * 40f ) ) visible.Add( bot.GameObject.Id );
		foreach ( var old in Contacts.Where( id => !visible.Contains( id ) ).ToArray() ) Contacts.Remove( old );
		foreach ( var id in visible ) if ( !Contacts.Contains( id ) ) Contacts.Add( id );
	}

	public bool IsFriendlyTo( Pawn viewer ) => viewer.IsValid()
		&& (GameUtils.IsFreeForAllMode ? viewer == Operator : viewer.Team == ReconTeam && ReconTeam != Team.Unassigned);

	public static bool Reveals( GameObject target, Pawn viewer ) => target.IsValid() && viewer.IsValid()
		&& target.Scene.GetAllComponents<ReconDroneFlight>().Any( drone => drone.IsScanning
			&& drone.IsFriendlyTo( viewer ) && drone.Contacts.Contains( target.Id ) );

	protected override void OnUpdate()
	{
		if ( !Propeller.IsValid() ) return;
		propellerAngle = (propellerAngle + Time.Delta * 2800f) % 360f;
		Propeller.LocalRotation = Rotation.FromRoll( propellerAngle );
	}

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent e )
	{
		if ( Networking.IsHost ) GameObject.Destroy();
	}
	bool IMinimapElement.IsVisible( Pawn viewer ) => IsFriendlyTo( viewer );
	Vector3 IMinimapElement.WorldPosition => WorldPosition;
	string IMinimapIcon.IconPath => "ui/weapons/recon_drone.svg";
	string ICustomMinimapIcon.CustomStyle => $"background-image-tint: {ReconTeam.GetColor().Hex}";
}
