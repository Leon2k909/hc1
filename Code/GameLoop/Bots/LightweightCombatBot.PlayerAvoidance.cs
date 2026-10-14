namespace Facepunch;

public sealed partial class LightweightCombatBot
{
	private const float PlayerPassClearance = 44f;
	private Vector3? _playerDetour;
	private Vector3? _playerPassPoint;
	private TimeUntil _playerDetourEnds;

	/// <summary>
	/// Players aren't navmesh agents. Take two short steps around one blocking the route, keeping the original goal.
	/// Just stopping and trying the same route again left bots waiting in front of a stationary player indefinitely.
	/// </summary>
	private bool WaitForPlayer()
	{
		if ( _playerDetour.HasValue )
			return ContinuePlayerDetour();

		if ( _playerInTheWay.Relative > 0f )
			return true;
		if ( !_moveTarget.HasValue || !Agent.IsNavigating )
			return false;

		// Use the route even when starting from rest. Leave braking room before turning away from a player.
		var ahead = (Agent.GetLookAhead( 80f ) - WorldPosition).WithZ( 0f ).Normal;
		if ( ahead.IsNearZeroLength )
			return false;
		var speed = Agent.Velocity.WithZ( 0f ).Length;
		var distance = 56f + speed * 0.1f + speed * speed / (2f * MathF.Max( Agent.Acceleration, 1f ));
		PlayerPawn blocker = null;
		var nearest = distance;
		foreach ( var player in LivingPawns )
		{
			var offset = player.WorldPosition - WorldPosition;
			if ( MathF.Abs( offset.z ) > 64f )
				continue;
			var flat = offset.WithZ( 0f );
			var along = flat.Dot( ahead );
			if ( along < 0f || along > nearest || (flat - ahead * along).Length > PlayerPassClearance )
				continue;
			blocker = player;
			nearest = along;
		}

		if ( !blocker.IsValid() )
			return false;
		if ( TryPlayerDetour( blocker, ahead ) )
			return true;

		// A doorway may have no room to pass. Yield briefly, then check again instead of walking into the player.
		HoldPosition();
		_playerInTheWay = 0.25f;
		return true;
	}

	private bool TryPlayerDetour( PlayerPawn player, Vector3 ahead )
	{
		var side = Vector3.Cross( ahead, Vector3.Up );
		if ( Game.Random.Float() < 0.5f )
			side = -side;

		for ( var width = 80f; width <= 112f; width += 32f )
		{
			for ( var sign = 1; sign >= -1; sign -= 2 )
			{
				// First step sideways; only then go beyond them. A single diagonal waypoint can still clip their box.
				var offset = side * (width * sign);
				var shoulder = NavPoint( WorldPosition + offset - ahead * 16f );
				var beyond = NavPoint( player.WorldPosition.WithZ( WorldPosition.z ) + offset + ahead * 96f );
				if ( shoulder.WithZ( 0f ).Distance( (WorldPosition + offset - ahead * 16f).WithZ( 0f ) ) > 24f
					|| beyond.WithZ( 0f ).Distance( (player.WorldPosition + offset + ahead * 96f).WithZ( 0f ) ) > 24f
					|| OutsideZone( shoulder ) || OutsideZone( beyond )
					|| !TryPlayerStep( WorldPosition, shoulder, out var path )
					|| !TryPlayerStep( shoulder, beyond, out _ ) )
					continue;

				StandFromProne();
				IsCrouching = false;
				_playerDetour = shoulder;
				_playerPassPoint = beyond;
				_playerDetourEnds = 3f;
				// Stop the old forward momentum before stepping aside; keep it at a walk and able to shoot.
				Agent.Stop();
				Agent.MaxSpeed = MathF.Min( Agent.MaxSpeed, 140f );
				Agent.SetPath( path );
				return true;
			}
		}

		return false;
	}

	private bool ContinuePlayerDetour()
	{
		if ( _playerDetourEnds.Relative <= 0f )
		{
			HoldPosition();
			return false;
		}

		if ( WorldPosition.WithZ( 0f ).DistanceSquared( _playerDetour.Value.WithZ( 0f ) ) < 20f * 20f )
		{
			if ( _playerPassPoint is { } beyond && TryPlayerStep( WorldPosition, beyond, out var path ) )
			{
				_playerDetour = beyond;
				_playerPassPoint = null;
				_playerDetourEnds = 3f;
				Agent.SetPath( path );
				return true;
			}

			// Let the usual combat/objective decision resume, issuing the original destination again if still needed.
			HoldPosition();
			return false;
		}

		// If someone steps into this detour, stop and plan again. Do not keep following an obsolete clear path.
		var stride = MathF.Max( 48f, Agent.Velocity.WithZ( 0f ).Length * 0.3f );
		if ( !PlayerSegmentClear( WorldPosition, Agent.GetLookAhead( stride ), checkWorld: false ) )
		{
			HoldPosition();
			_playerInTheWay = 0.15f;
		}
		return true;
	}

	private void ClearPlayerDetour()
	{
		_playerDetour = null;
		_playerPassPoint = null;
	}

	/// <summary> Validate the actual navmesh corners, so a path around a wall can't secretly cross the player. </summary>
	private bool TryPlayerStep( Vector3 from, Vector3 to, out Sandbox.Navigation.NavMeshPath path )
	{
		path = Scene.NavMesh.CalculatePath( new Sandbox.Navigation.CalculatePathRequest { Start = from, Target = to, Agent = Agent } );
		if ( path.Status != Sandbox.Navigation.NavMeshPathStatus.Complete || path.Points is not { Count: > 0 } )
			return false;

		var previous = from;
		var length = 0f;
		foreach ( var corner in path.Points )
		{
			length += previous.Distance( corner.Position );
			if ( length > 400f || !PlayerSegmentClear( previous, corner.Position ) )
				return false;
			previous = corner.Position;
		}
		return PlayerSegmentClear( previous, to );
	}

	private bool PlayerSegmentClear( Vector3 from, Vector3 to, bool checkWorld = true )
	{
		if ( checkWorld && Scene.Trace.Ray( from, to )
			.Size( new Vector3( -18f, -18f, 2f ), new Vector3( 18f, 18f, 62f ) )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "corpse", "ragdoll", "player", "movement", LightweightBotManager.BotTag )
			.Run().Hit )
			return false;

		var travel = (to - from).WithZ( 0f );
		// A path's first corner can be directly under the bot. It must still be able to step out of an existing overlap.
		if ( travel.LengthSquared < 0.01f )
			return true;
		foreach ( var player in LivingPawns )
		{
			if ( MathF.Abs( player.WorldPosition.z - from.z ) > 64f && MathF.Abs( player.WorldPosition.z - to.z ) > 64f )
				continue;
			var offset = (player.WorldPosition - from).WithZ( 0f );
			var along = travel.LengthSquared > 0.01f ? (offset.Dot( travel ) / travel.LengthSquared).Clamp( 0f, 1f ) : 0f;
			if ( (offset - travel * along).Length >= PlayerPassClearance )
				continue;
			// Already too close: allow a step away, but never one that reduces the gap further.
			if ( offset.Length < PlayerPassClearance && offset.Dot( travel ) <= 0f && travel.LengthSquared > 0.01f )
				continue;
			return false;
		}
		return true;
	}
}
