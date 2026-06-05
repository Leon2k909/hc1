using Facepunch;

namespace Tec;

public class DoorNavMeshLink : NavMeshLink
{
	[Property] public Door Door { get; private set; }

	private bool _closePending = false;
	
	protected override void OnLinkEntered( NavMeshAgent agent )
	{
		if ( Door.State == Door.DoorState.Closed )
		{
			_closePending = true;
			var pawn = agent.GetComponentInParent<PlayerPawn>();
			Door.OnUse(pawn);
		}
	}

	protected override void OnLinkExited( NavMeshAgent agent )
	{
		if ( !_closePending ) return;

		_closePending = false;
		var pawn = agent.GetComponentInParent<PlayerPawn>();
		Door.OnUse( pawn );
	}
}
