using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public sealed class ZombiesGameMode : Component, IGameEventHandler<PlayerSpawnedEvent>
{
	// Serialized model references keep cloud assets in the game's dependency graph.
	[Property] public Model ZombieBodyModel { get; set; }
	[Property] public Model MysteryBoxModel { get; set; }

	protected override void OnAwake()
	{
		base.OnAwake();
		if ( Networking.IsHost )
		{
			var rounds = Components.GetOrCreate<ZombiesRoundSystem>();
			rounds.ZombieBodyModel = ZombieBodyModel;
			rounds.MysteryBoxModel = MysteryBoxModel;
		}
	}

	protected override void OnStart()
	{
		base.OnStart();

		if ( Networking.IsHost )
		{
			CarriedPoints.Clear();
			foreach ( var p in Scene.GetAllComponents<PlayerPawn>() )
				SetupPlayer( p );
		}
	}

	void IGameEventHandler<PlayerSpawnedEvent>.OnGameEvent( PlayerSpawnedEvent eventArgs )
	{
		if ( Networking.IsHost && eventArgs.Player.IsValid() )
			SetupPlayer( eventArgs.Player );
	}

	private static void SetupPlayer( PlayerPawn player )
	{
		// Points carry over between lives; a restart resets them.
		if ( !player.Components.TryGet<ZombiesPlayerEconomy>( out _ ) )
		{
			var eco = player.Components.Create<ZombiesPlayerEconomy>();
			if ( player.Client.IsValid() && CarriedPoints.TryGetValue( player.Client, out var pts ) )
				eco.SetPoints( pts );
		}

		if ( !player.Components.TryGet<ZombiesPlayerState>( out var state ) )
			state = player.Components.Create<ZombiesPlayerState>();

		state.ResetState();
		ZombiesRoundSystem.Current?.OnPlayerSpawned( player );
	}

	/// <summary>Points saved when a pawn is destroyed on death, restored when the player respawns.</summary>
	public static readonly Dictionary<Client, int> CarriedPoints = new();
}
