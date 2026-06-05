using Tec;

namespace Facepunch;

public class AwareBehavior : BaseBotBehavior
{
	private IBehaviorNode _behavior;

	public override float Score( BotContext ctx )
	{
		// Use perception data that BotPlayerController already populated
		var hasSounds = ctx.HasData( AIConst.ALERT_SOUNDS_KEY );
		var hasAlertPosition = ctx.HasData( AIConst.ALERT_POS );
		if ( !hasSounds && !hasAlertPosition )
			return 0f;

		float baseScore = 50f;
		float closestDistSqr = float.MaxValue;
		var pawnPosition = ctx.Pawn.WorldPosition;

		if ( hasSounds )
		{
			var sounds = ctx.GetData<List<Vector3>>( AIConst.ALERT_SOUNDS_KEY );
			if ( sounds is not null )
			{
				foreach ( var sound in sounds )
				{
					closestDistSqr = MathF.Min( closestDistSqr, sound.DistanceSquared( pawnPosition ) );
				}
			}
		}

		if ( hasAlertPosition )
		{
			closestDistSqr = MathF.Min( closestDistSqr, ctx.GetData<Vector3>( AIConst.ALERT_POS ).DistanceSquared( pawnPosition ) );
		}

		if ( closestDistSqr == float.MaxValue )
			return 0f;

		// Simple scoring: higher when sounds are closer
		float closestDist = MathF.Sqrt( closestDistSqr );
		float proximityBonus = MathF.Max( 0, 50f * (1f - closestDist / 1000f) );

		return baseScore + proximityBonus;
	}

	protected override void OnInitialize()
	{
		// Build behavior tree
		_behavior = new SequenceNode(
			new MoveToAlertNode()
		);
	}

	public override NodeResult Update( BotContext ctx )
	{
		return _behavior.Evaluate( ctx );
	}
}
