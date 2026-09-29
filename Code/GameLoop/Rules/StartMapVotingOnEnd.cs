using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Show a warning message when entering this state, then throw everyone back to the menu when this state ends.
/// </summary>
public sealed class StartMapVotingOnEnd : Component,
	IGameEventHandler<EnterStateEvent>
{
	void IGameEventHandler<EnterStateEvent>.OnGameEvent( EnterStateEvent eventArgs )
	{
		// Show end-of-match screen from the host first, then start map vote.
		if ( Networking.IsHost )
		{
			var winningTeam = GameMode.Instance?.Get<TeamScoring>()?.GetHighest() ?? Team.Unassigned;
			var ranked = GameMode.Instance?.FinishRankedMatch( winningTeam ) ?? false;
			Facepunch.UI.EndOfMatchScreen.Show( winningTeam );
			if ( ranked ) return;
		}

		// Start the vote system
		if ( Networking.IsHost ) MapVoteSystem.Create();
	}
}
