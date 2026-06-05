using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Gives players their current gun game tier weapon when they respawn.
/// </summary>
public sealed class GunGameRespawner : Component,
	IGameEventHandler<PlayerSpawnedEvent>
{
	void IGameEventHandler<PlayerSpawnedEvent>.OnGameEvent( PlayerSpawnedEvent eventArgs )
	{
		if ( !Networking.IsHost ) return;

		var manager = GameMode.Instance?.GetComponentInChildren<GunGameManager>();
		if ( !manager.IsValid() ) return;

		manager.OnPlayerRespawned( eventArgs.Player );
	}
}
