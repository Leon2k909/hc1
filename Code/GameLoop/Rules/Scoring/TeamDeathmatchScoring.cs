using Facepunch;
using Sandbox.Events;

namespace Facepunch;

public sealed class TeamDeathmatchScoring : Component,
	IGameEventHandler<KillEvent>
{
	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		if ( !Networking.IsHost )
			return;

		var damageInfo = eventArgs.DamageInfo;

		var killerTeam = GameUtils.GetTeamFromComponent( damageInfo.Attacker );
		if ( killerTeam == Team.Unassigned )
			return;

		var victimTeam = GameUtils.GetTeamFromComponent( damageInfo.Victim );
		if ( victimTeam == Team.Unassigned )
			return;

		if ( killerTeam == victimTeam )
			return;

		GameMode.Instance.Get<TeamScoring>()?.IncrementScore( killerTeam );
	}
}
