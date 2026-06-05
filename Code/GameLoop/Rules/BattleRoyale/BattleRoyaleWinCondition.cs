using Sandbox;
using Sandbox.Events;
using System.Linq;
using System.Collections.Generic;

namespace Facepunch;

/// <summary>
/// Transitions to another state if there is only one team or player left alive.
/// </summary>
public sealed class BattleRoyaleWinCondition : Component,
	IGameEventHandler<UpdateStateEvent>
{
	[Property]
	public StateComponent MatchEndedState { get; set; }

	private bool IsMatchOver()
	{
		var allPlayers = GameUtils.PlayerPawns.ToList();
		if ( !allPlayers.Any() ) return false;

		// Group alive players by team
		var aliveTeams = new HashSet<Team>();
		int unassignedAliveCount = 0;

		foreach ( var player in allPlayers )
		{
			if ( player.HealthComponent is null || player.HealthComponent.State != LifeState.Alive )
				continue;

			var team = player.Team;
			if ( team == Team.Unassigned )
			{
				unassignedAliveCount++;
			}
			else
			{
				aliveTeams.Add( team );
			}
		}

		int totalFactionsAlive = aliveTeams.Count + unassignedAliveCount;
		
		// If 1 or 0 factions are alive, the game is over!
		return totalFactionsAlive <= 1;
	}

	void IGameEventHandler<UpdateStateEvent>.OnGameEvent( UpdateStateEvent eventArgs )
	{
		if ( !Networking.IsHost ) return;
		
		// Don't end immediately if we just started and players are still spawning
		if ( Time.Now < 3f ) return;

		if ( IsMatchOver() && MatchEndedState is not null )
		{
			GameMode.Instance.StateMachine.Transition( MatchEndedState );
		}
	}
}
