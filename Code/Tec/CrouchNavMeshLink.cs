using Facepunch;

namespace Tec;

public class CrouchNavMeshLink : NavMeshLink
{
	protected override void OnLinkEntered( NavMeshAgent agent )
	{
		var pawn = agent.GetComponentInParent<PlayerPawn>();
		pawn.IsCrouching = true;
	}

	protected override void OnLinkExited( NavMeshAgent agent )
	{
		var pawn = agent.GetComponentInParent<PlayerPawn>();
		pawn.IsCrouching = false;
		// Log.Info($"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee");
	}
}
