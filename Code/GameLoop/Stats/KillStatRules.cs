namespace Facepunch;

/// <summary>Career and weapon kill rewards share the same enemy-soldier eligibility.</summary>
internal static class KillStatRules
{
	internal static bool IsEnemyKill( DamageInfo damage )
	{
		if ( !damage.Attacker.IsValid() || !damage.Victim.IsValid()
			|| damage.Attacker.GameObject.Root == damage.Victim.GameObject.Root )
			return false;

		if ( !GameUtils.GetPlayerFromComponent( damage.Victim ).IsValid()
			&& !GameUtils.GetLightweightBotFromComponent( damage.Victim ).IsValid() )
			return false;

		var team = GameUtils.GetTeamFromComponent( damage.Attacker );
		return team == Team.Unassigned || team != GameUtils.GetTeamFromComponent( damage.Victim );
	}
}
