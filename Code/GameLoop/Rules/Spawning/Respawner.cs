using Sandbox.Events;

namespace Facepunch;

public abstract class Respawner : Component,
	IGameEventHandler<UpdateStateEvent>
{
	[Property, Sync( SyncFlags.FromHost )] public float RespawnDelaySeconds { get; set; } = 3f;
	[Property] public bool AllowSpectatorsToSpawn { get; set; } = false;

	/// <summary>
	/// How long until respawn?
	/// </summary>
	/// <returns></returns>
	public int GetRespawnTime()
	{
		return (RespawnDelaySeconds - Client.Local.TimeSinceRespawnStateChanged).Clamp( 0f, RespawnDelaySeconds ).CeilToInt();
	}

	void IGameEventHandler<UpdateStateEvent>.OnGameEvent( UpdateStateEvent eventArgs )
	{
		foreach ( var player in GameUtils.AllPlayers )
		{
			if ( player.PlayerPawn.IsValid() && player.PlayerPawn.HealthComponent.State == LifeState.Alive )
				continue;

			if ( !player.IsConnected )
				continue;

			// Zombies: players who died wait for the next round.
			if ( ZombiesRoundSystem.Current?.ShouldHoldRespawn( player ) == true )
				continue;

			// Don't auto-respawn bots - they respawn via round events in round-based modes
			if ( player.IsBot )
				continue;

			if ( !AllowSpectatorsToSpawn && player.Team == Team.Unassigned )
			{
				// don't spawn these guys right now
				continue;
			}

			switch ( player.RespawnState )
			{
				case RespawnState.Requested:
					player.RespawnState = RespawnState.Delayed;

					// An instant respawn (a custom game's) has nothing to wait for.
					if ( !player.IsBot && RespawnDelaySeconds > 0f )
					{
						using ( Rpc.FilterInclude( player.Connection ) )
						{
							GameMode.Instance.ShowToast( "Respawning...", duration: RespawnDelaySeconds );
						}
					}

					break;

				case RespawnState.Delayed:
					if ( player.TimeSinceRespawnStateChanged > RespawnDelaySeconds )
					{
						player.RespawnState = RespawnState.Immediate;
					}
					break;

				case RespawnState.Immediate:
					player.Respawn( true );
					break;
			}
		}
	}
}
