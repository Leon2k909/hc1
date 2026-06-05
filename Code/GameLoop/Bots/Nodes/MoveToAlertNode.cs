using Tec;

namespace Facepunch;

/// <summary>
/// Moves the bot to a target position using navmesh pathfinding
/// </summary>
public class MoveToAlertNode : BaseBehaviorNode
{
	private readonly float _searchingTime;
	private readonly float _arrivalDistance;
	private readonly bool _faceDirection;
	private bool running;
	private TimeSince timeSinceLastAlertStim;

	public MoveToAlertNode( float searchingTime = 30f, float arrivalDistance = 128f, bool faceDirection = true )
	{
		_searchingTime = searchingTime;
		_arrivalDistance = arrivalDistance;
		_faceDirection = faceDirection;
	}

	protected override NodeResult OnEvaluate( BotContext context )
	{
		if ( running && timeSinceLastAlertStim > _searchingTime )
		{
			running = false;
			context.RemoveData( AIConst.ALERT_POS );
			PrintOverlay.Print("I give up searching!");
			return NodeResult.Failure;
		}
		
		var hasSounds = context.HasData( AIConst.ALERT_SOUNDS_KEY );
		var hasAlertPosition = context.HasData( AIConst.ALERT_POS );
		var pawnPosition = context.Pawn.WorldPosition;
		var targetPos = Vector3.Zero;
		var targetDistSqr = float.MaxValue;

		if ( hasSounds )
		{
			var sounds = context.GetData<List<Vector3>>( AIConst.ALERT_SOUNDS_KEY );
			if ( sounds is not null )
			{
				foreach ( var sound in sounds )
				{
					var distSqr = sound.DistanceSquared( pawnPosition );
					if ( distSqr < targetDistSqr )
					{
						targetPos = sound;
						targetDistSqr = distSqr;
					}
				}
			}
		}

		if ( hasAlertPosition )
		{
			var alertPos = context.GetData<Vector3>( AIConst.ALERT_POS );
			var alertDistSqr = alertPos.DistanceSquared( pawnPosition );
			if ( alertDistSqr < targetDistSqr )
			{
				targetPos = alertPos;
				targetDistSqr = alertDistSqr;
			}
		}

		if ( targetDistSqr == float.MaxValue )
		{
			running = false;
			return NodeResult.Failure;
		}

		if ( running && context.HasData( AIConst.ALERT_POS ) && targetPos != context.GetData<Vector3>( AIConst.ALERT_POS ) )
		{
			timeSinceLastAlertStim = 0;
		}
		
		context.SetData( AIConst.ALERT_POS, targetPos );

		if ( !running )
		{
			timeSinceLastAlertStim = 0;
			running = true;
		}
		
		var pawn = context.Pawn;
		var agent = context.MeshAgent;

		if ( !agent.IsValid() )
			return NodeResult.Failure;
		
		// Step agent toward target
		agent.MoveTo( targetPos );

		// Check if we've reached target
		float arrivalDistSqr = pawn.WorldPosition.DistanceSquared( targetPos );
		if ( arrivalDistSqr < _arrivalDistance * _arrivalDistance )
		{
			context.RemoveData( AIConst.ALERT_POS );
			return NodeResult.Success;
		}

		// Face movement direction if desired
		if ( _faceDirection && agent.WishVelocity.Length > 0.1f )
		{
			var targetRot = Rotation.LookAt( agent.WishVelocity.Normal );
			pawn.EyeAngles = pawn.EyeAngles.LerpTo( targetRot.Angles(), Time.Delta * 5f );
		}

		return NodeResult.Running;
	}
}
