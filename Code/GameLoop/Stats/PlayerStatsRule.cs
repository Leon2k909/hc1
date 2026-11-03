using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// If added to a gamemode, we'll record player stats while in this state.
/// </summary>
public sealed class PlayerStatsRule : Component,
	IGameEventHandler<KillEvent>
{
	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		if ( !Networking.IsHost ) return;

		SendToAttacker( eventArgs );
		SendToVictim( eventArgs );
	}

	private void SendToAttacker( KillEvent eventArgs )
	{
		var player = GameUtils.GetPlayerFromComponent( eventArgs.DamageInfo.Attacker );
		if ( !player.IsValid() )
			return;

		// Bots don't care about stats
		if ( !player.Client.IsValid() || player.Client.IsBot )
			return;

		if ( !KillStatRules.IsEnemyKill( eventArgs.DamageInfo ) )
			return;

		var inflictor = eventArgs.DamageInfo.Inflictor;
		if ( inflictor is Equipment wpn && wpn.IsValid() )
		{
			using ( Rpc.FilterInclude( player.Network.Owner ) )
			{
				SendKillStat( eventArgs.DamageInfo.Hitbox );
			}
		}
	}

	/// <summary>
	/// Send a death stat to the human victim, including deaths to bots, falls and other world damage.
	/// </summary>
	/// <param name="eventArgs"></param>
	private void SendToVictim( KillEvent eventArgs )
	{
		var player = GameUtils.GetPlayerFromComponent( eventArgs.DamageInfo.Victim );
		if ( !player.IsValid() )
			return;

		// Player left?
		if ( !player.Client.IsValid() )
			return;

		// Bots don't care about stats
		if ( player.Client.IsBot )
			return;

		using ( Rpc.FilterInclude( player.Network.Owner ) )
		{
			SendDeathStat();
		}
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void SendKillStat( HitboxTags hitbox = default )
	{
		var isHeadshot = hitbox.HasFlag( HitboxTags.Head );

		if ( isHeadshot )
		{
			Stats.Increment( "kills-headshots" );
		}

		Stats.Increment( "kills" );

		// Player progression XP: 150 for headshot, 100 for regular kill
		Progression.AddXP( isHeadshot ? 150 : 100 );
		DailyChallenges.OnKill( isHeadshot );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void SendDeathStat()
	{
		Stats.Increment( "deaths" );
	}
}
