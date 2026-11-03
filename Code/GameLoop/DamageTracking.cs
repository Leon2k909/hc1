using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Track damage for every single player so we can call it back.
/// </summary>
public partial class DamageTracker : Component, IGameEventHandler<DamageTakenGlobalEvent>,
	IGameEventHandler<BetweenRoundCleanupEvent>,
	IGameEventHandler<PlayerSpawnedEvent>
{
	[Property] public bool ClearBetweenRounds { get; set; } = true;
	[Property] public bool ClearOnRespawn { get; set; } = false;

	public Dictionary<Client, List<DamageInfo>> Registry { get; set; } = new();
	/// <summary>Damage dealt by the local client, keyed by that client rather than the targets.</summary>
	public Dictionary<Client, List<DamageInfo>> MyInflictedDamage { get; set; } = new();

	[Rpc.Broadcast( NetFlags.HostOnly )]
	protected void RpcRefresh()
	{
		Refresh();
	}

	public List<DamageInfo> GetDamageOnMe()
	{
		return GetDamageInflictedTo( Client.Local );
	}

	public List<DamageInfo> GetDamageInflictedTo( Client player )
	{
		if ( !Registry.TryGetValue( player, out var list ) )
		{
			return new List<DamageInfo>();
		}

		return list;
	}

	public List<DamageInfo> GetMyInflictedDamage( Client player )
	{
		if ( !MyInflictedDamage.TryGetValue( player, out var list ) )
		{
			return new List<DamageInfo>();
		}

		return list;
	}

	public struct GroupedDamage
	{
		public Component Attacker { get; set; }
		public Component Victim { get; set; }
		public int Count { get; set; }
		public float Damage { get; set; }
	}

	public List<GroupedDamage> GetGroupedDamage( Client player )
	{
		var groups = new List<GroupedDamage>();

		GetDamageInflictedTo( player )
			.GroupBy( x => x.Attacker )
			.ToList()
			.ForEach( group =>
			{
				groups.Add( new()
				{
					Attacker = group.First().Attacker,
					Count = group.Count(),
					Damage = group.Sum( x => x.Damage )
				} );
			} );


		return groups;
	}

	public List<GroupedDamage> GetGroupedInflictedDamage( Client player )
	{
		var groups = new List<GroupedDamage>();

		GetMyInflictedDamage( player )
			.GroupBy( x => x.Victim )
			.ToList()
			.ForEach( group =>
			{
				groups.Add( new()
				{
					Attacker = group.First().Attacker,
					Victim = group.Key,
					Count = group.Count(),
					Damage = group.Sum( x => x.Damage )
				} );
			} );


		return groups;
	}

	public void Refresh()
	{
		MyInflictedDamage.Clear();
		Registry.Clear();
	}

	void IGameEventHandler<DamageTakenGlobalEvent>.OnGameEvent( DamageTakenGlobalEvent eventArgs )
	{
		var attackerPlayer = GameUtils.GetPlayerFromComponent( eventArgs.DamageInfo.Attacker );
		var victimPlayer = GameUtils.GetPlayerFromComponent( eventArgs.DamageInfo.Victim );
		var damage = eventArgs.DamageInfo with
		{
			Attacker = attackerPlayer.IsValid() ? attackerPlayer : eventArgs.DamageInfo.Attacker,
			Victim = victimPlayer.IsValid() ? victimPlayer : eventArgs.DamageInfo.Victim
		};
		var attackerClient = (damage.Attacker as Pawn)?.Client;
		var victimClient = (damage.Victim as Pawn)?.Client;

		// Record outgoing hits before requiring a client on the victim: bots and NPCs have none.
		if ( attackerClient.IsValid() && attackerClient == Client.Local && damage.Victim.IsValid() )
		{
			if ( !MyInflictedDamage.TryGetValue( attackerClient, out var myList ) )
			{
				MyInflictedDamage.Add( attackerClient, new() { damage } );
			}
			else
			{
				myList.Add( damage );
			}
		}

		if ( !victimClient.IsValid() ) return;

		if ( !Registry.TryGetValue( victimClient, out var list ) )
		{
			Registry.Add( victimClient, new() { damage } );
		}
		else
		{
			list.Add( damage );
		}
	}

	/// <summary>
	/// Called between rounds.
	/// </summary>
	/// <param name="eventArgs"></param>
	void IGameEventHandler<BetweenRoundCleanupEvent>.OnGameEvent( BetweenRoundCleanupEvent eventArgs )
	{
		if ( !ClearBetweenRounds ) return;
		
		// This is called for everyone, so we don't need another RPC.

		// Get rid of old data since the rounds refreshed.
		Refresh();
	}

	void IGameEventHandler<PlayerSpawnedEvent>.OnGameEvent( PlayerSpawnedEvent eventArgs )
	{
		if ( !ClearOnRespawn ) return;

		// Only include the owner
		using ( Rpc.FilterInclude( eventArgs.Player.Network.Owner ) )
		{
			// Send the refresh
			RpcRefresh();
		}
	}
}
