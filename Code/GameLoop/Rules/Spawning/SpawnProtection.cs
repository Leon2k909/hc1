using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Dispatched on the host when a player starts being spawn protected.
/// </summary>
public record SpawnProtectionStartEvent( PlayerPawn Player ) : IGameEvent;

/// <summary>
/// Dispatched on the host when a player stops being spawn protected.
/// </summary>
public record SpawnProtectionEndEvent( PlayerPawn Player ) : IGameEvent;

/// <summary>Dispatched by a player when they fire a weapon.</summary>
public record PlayerFiredWhileSpawnedEvent( PlayerPawn Player ) : IGameEvent;

/// <summary>
/// Makes respawned players invulnerable for a given duration, or until they move / shoot.
/// </summary>
public sealed class SpawnProtection : Component,
	IGameEventHandler<PlayerSpawnedEvent>,
	IGameEventHandler<PlayerFiredWhileSpawnedEvent>
{
	private readonly Dictionary<PlayerPawn, TimeSince> _spawnProtectedSince = new();

	[Property, Sync( SyncFlags.FromHost )]
	public float MaxDurationSeconds { get; set; } = 10f;

	[Property, Sync( SyncFlags.FromHost )]
	public float MinimumDurationSeconds { get; set; } = 3f;

	void IGameEventHandler<PlayerSpawnedEvent>.OnGameEvent( PlayerSpawnedEvent eventArgs )
	{
		// Zombies spawns players out of harm's way between rounds; no deathmatch-style protection.
		if ( ZombiesRoundSystem.Current.IsValid() ) return;

		Enable( eventArgs.Player );
	}

	void IGameEventHandler<PlayerFiredWhileSpawnedEvent>.OnGameEvent( PlayerFiredWhileSpawnedEvent eventArgs )
	{
		if ( Networking.IsHost && _spawnProtectedSince.ContainsKey( eventArgs.Player ) )
			Disable( eventArgs.Player );
	}

	public void DisableAll()
	{
		foreach ( var (player, _) in _spawnProtectedSince.ToArray() )
		{
			Disable( player );
		}
	}

	protected override void OnDisabled()
	{
		DisableAll();
	}

	protected override void OnFixedUpdate()
	{
		if ( !Networking.IsHost || _spawnProtectedSince.Count == 0 )
		{
			return;
		}

		foreach ( var (player, since) in _spawnProtectedSince.ToArray() )
		{
			if ( !player.IsValid() || since > MaxDurationSeconds
				|| (since > MinimumDurationSeconds && player.TimeSinceLastInput < since + 0.1f) )
			{
				Disable( player );
			}
		}
	}

	public void Enable( PlayerPawn player )
	{
		_spawnProtectedSince[player] = 0f;

		player.HealthComponent.IsGodMode = true;

		if ( !player.Client.IsBot )
		{
			using ( Rpc.FilterInclude( player.Client.Connection ) )
			{
				GameMode.Instance.ShowToast( "Spawn Protected", duration: MaxDurationSeconds );
			}
		}

		Scene.Dispatch( new SpawnProtectionStartEvent( player ) );
	}

	public void Disable( PlayerPawn player )
	{
		if ( !_spawnProtectedSince.Remove( player ) )
			return;

		if ( !player.IsValid() )
			return;
		player.HealthComponent.IsGodMode = false;

		if ( player.Client.IsValid() && player.Network.Active && player.Client.Network.Active )
		{
			using ( Rpc.FilterInclude( player.Client.Connection ) )
			{
				GameMode.Instance.HideToast();
			}
		}

		Scene.Dispatch( new SpawnProtectionEndEvent( player ) );
	}
}
