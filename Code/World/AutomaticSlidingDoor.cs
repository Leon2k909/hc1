namespace Facepunch;

/// <summary>
/// A two-leaf proximity door for authored maps. Snapshot map objects use host-only
/// static RPCs; explicit closed positions also make late-join snapshots unambiguous.
/// </summary>
public sealed class AutomaticSlidingDoor : Component, Component.INetworkListener
{
	[Property] public GameObject LeftLeaf { get; set; }
	[Property] public GameObject RightLeaf { get; set; }
	[Property] public Vector3 LeftClosedPosition { get; set; } = new( 0, 44, 96 );
	[Property] public Vector3 RightClosedPosition { get; set; } = new( 0, -44, 96 );
	[Property] public float Width { get; set; } = 176;
	[Property] public float Height { get; set; } = 192;
	[Property] public float Travel { get; set; } = 91;
	[Property] public float ApproachDistance { get; set; } = 144;
	[Property] public float OpenTime { get; set; } = .65f;
	[Property] public float CloseTime { get; set; } = 1f;
	[Property] public float CloseDelay { get; set; } = 1.5f;

	public float OpenFraction { get; private set; }
	public bool WantsOpen { get; private set; }
	TimeSince _sinceOccupied;
	TimeSince _sinceScan = 1;
	bool _navMeshUpdated;

	protected override void OnStart()
	{
		Tags.Add( "door" );
		if ( LeftLeaf.IsValid() ) LeftLeaf.Tags.Add( "door" );
		if ( RightLeaf.IsValid() ) RightLeaf.Tags.Add( "door" );
		Scene.NavMesh.ExcludedBodies.Add( "door" );
		ApplyPose();
	}

	/// <summary> Actor feet in the approach area on either side of the frame. </summary>
	public bool ContainsActorPosition( Vector3 worldPosition )
	{
		var local = WorldTransform.PointToLocal( worldPosition );
		return MathF.Abs( local.x ) <= MathF.Max( 32, ApproachDistance )
			&& MathF.Abs( local.y ) <= Width * .5f + 32
			&& local.z >= -16 && local.z <= Height - 8;
	}

	bool HasNearbyActor()
	{
		foreach ( var pawn in Scene.GetAllComponents<PlayerPawn>() )
			if ( pawn.IsValid() && pawn.HealthComponent.IsValid()
				&& pawn.HealthComponent.State == LifeState.Alive && ContainsActorPosition( pawn.WorldPosition ) )
				return true;
		foreach ( var bot in Scene.GetAllComponents<LightweightCombatBot>() )
			if ( bot.IsValid() && bot.IsAlive && ContainsActorPosition( bot.WorldPosition ) ) return true;
		foreach ( var zombie in Scene.GetAllComponents<ZombieAI>() )
			if ( zombie.IsValid() && zombie.Health > 0 && ContainsActorPosition( zombie.WorldPosition ) ) return true;
		return false;
	}

	void SetTarget( bool open )
	{
		if ( WantsOpen == open ) return;
		BroadcastState( GameObject.Id, OpenFraction, open );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	static void BroadcastState( Guid objectId, float fraction, bool open )
	{
		var door = Game.ActiveScene?.Directory.FindByGuid( objectId )?.GetComponent<AutomaticSlidingDoor>();
		if ( !door.IsValid() ) return;
		door.OpenFraction = Math.Clamp( fraction, 0f, 1f );
		door.WantsOpen = open;
		door.ApplyPose();
	}

	void Component.INetworkListener.OnActive( Connection channel )
	{
		if ( !Networking.IsHost ) return;
		using ( Rpc.FilterInclude( channel ) )
			BroadcastState( GameObject.Id, OpenFraction, WantsOpen );
	}

	void ApplyPose()
	{
		var eased = OpenFraction * OpenFraction * (3f - 2f * OpenFraction);
		var delta = Vector3.Left * (MathF.Max( 0, Travel ) * eased);
		if ( LeftLeaf.IsValid() ) LeftLeaf.LocalPosition = LeftClosedPosition + delta;
		if ( RightLeaf.IsValid() ) RightLeaf.LocalPosition = RightClosedPosition - delta;
	}

	protected override void OnFixedUpdate()
	{
		if ( Networking.IsHost && _sinceScan >= .1f )
		{
			_sinceScan = 0;
			// Reversing as soon as somebody enters the approach area also prevents
			// the leaves closing on a player standing or returning through the gap.
			if ( HasNearbyActor() )
			{
				_sinceOccupied = 0;
				SetTarget( true );
			}
			else if ( _sinceOccupied >= MathF.Max( .2f, CloseDelay ) ) SetTarget( false );
		}

		var duration = MathF.Max( .05f, WantsOpen ? OpenTime : CloseTime );
		OpenFraction = Math.Clamp( OpenFraction + (WantsOpen ? 1f : -1f) * Time.Delta / duration, 0f, 1f );
		ApplyPose();

		if ( !_navMeshUpdated && Scene.NavMesh.IsEnabled && !Scene.NavMesh.IsGenerating )
		{
			_navMeshUpdated = true;
			Scene.NavMesh.RequestTilesGeneration( BBox.FromPositionAndSize(
				WorldPosition + Vector3.Up * (Height * .5f), new Vector3( Width + 128, Width + 128, Height + 48 ) ) );
		}
	}
}
