using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// If added to a gamemode, we'll record weapon stats while in this state.
/// </summary>
public sealed class WeaponStatsRule : Component,
	IGameEventHandler<KillEvent>
{
	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		var player = GameUtils.GetPlayerFromComponent( eventArgs.DamageInfo.Attacker );
		if ( !player.IsValid() )
			return;

		// Bots don't care about stats. The host owns their pawns, so a bot's kill would count as the host's.
		if ( !player.Client.IsValid() || player.Client.IsBot )
			return;

		var inflictor = eventArgs.DamageInfo.Inflictor;
		if ( inflictor is Equipment wpn && wpn.IsValid() )
		{
			using ( Rpc.FilterInclude( player.Network.Owner ) )
			{
				SendKillStat( wpn.Resource.ResourcePath, eventArgs.DamageInfo.Hitbox, eventArgs.DamageInfo.Flags );
			}
		}
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void SendKillStat( string resourcePath, HitboxTags hitbox = default, DamageFlags flags = default )
	{
		var resource = ResourceLibrary.Get<EquipmentResource>( resourcePath );
		if ( resource is not null )
		{
			var isHeadshot = hitbox == HitboxTags.Head;

			if ( isHeadshot )
			{
				WeaponStats.Increment( "kills-headshots", resource, flags );
			}

			WeaponStats.Increment( "kills", resource, flags );
			UsageStats.CountKill( resource );

			// Weapon progression XP: 75 for headshot, 50 for regular kill
			WeaponProgression.AddXP( resource, isHeadshot ? 75 : 50 );
		}
	}
}
