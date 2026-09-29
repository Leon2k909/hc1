using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Maintains a minimum player count by filling empty slots with bots.
/// Bots are removed as real players join.
/// Bots are respawned when a new round starts.
/// </summary>
public sealed class BotFillRule : Component,
	IGameEventHandler<PlayerJoinedEvent>,
	IGameEventHandler<PlayerDisconnectedEvent>,
	IGameEventHandler<EnterStateEvent>,
	IGameEventHandler<UpdateStateEvent>,
	IGameEventHandler<RoundCounterIncrementedEvent>
{
	private bool HasHostAuthority => !IsProxy || Networking.IsHost || (Connection.Local?.IsHost ?? false);

	/// <summary>
	/// Minimum number of players desired in the game
	/// </summary>
	[Property] public int MinPlayerCount { get; set; } = 10;
	[Property] public int MaxTeamSize { get; set; } = 5;
	[Property] public bool UseLightweightNpcBots { get; set; } = true;

	private List<Client> _addedBots = new();
	private TimeSince _timeSinceLastFillCheck;
	private bool _defuseRoundFillPending;
	private TimeSince _timeSinceDefuseReset;

	protected override void OnStart()
	{
		UpdatePlayerCount();
	}

	protected override void OnUpdate()
	{
		if ( _defuseRoundFillPending && _timeSinceDefuseReset > .1f )
		{
			_defuseRoundFillPending = false;
			UpdatePlayerCount();
		}
		UpdatePlayerCountThrottled();
	}

	void IGameEventHandler<UpdateStateEvent>.OnGameEvent( UpdateStateEvent eventArgs )
	{
		UpdatePlayerCountThrottled();
	}

	private void UpdatePlayerCountThrottled()
	{
		if ( _timeSinceLastFillCheck < 1f )
			return;

		_timeSinceLastFillCheck = 0;

		// In round-based modes, suppress continuous mid-round bot filling.
		// Bots are only respawned at round start via RoundCounterIncrementedEvent.
		if ( Scene.GetAllComponents<RoundCounter>().Any() )
			return;

		UpdatePlayerCount();
	}

	void IGameEventHandler<EnterStateEvent>.OnGameEvent( EnterStateEvent eventArgs )
	{
		UpdatePlayerCount();
	}

	void IGameEventHandler<RoundCounterIncrementedEvent>.OnGameEvent( RoundCounterIncrementedEvent eventArgs )
	{
		// Regular (Client) bots: respawn any that are dead
		RespawnDeadBots();
		// Lightweight bots: spawn replacements for any that were destroyed on death
		UpdatePlayerCount();
	}

	void IGameEventHandler<PlayerJoinedEvent>.OnGameEvent( PlayerJoinedEvent eventArgs )
	{
		if ( UseLightweightNpcBots )
		{
			UpdatePlayerCount();
			return;
		}

		if ( eventArgs.Player.IsBot )
			return;

		// Real player joined, potentially remove a bot if the fill target is exceeded.
		if ( GameUtils.AllPlayers.Count() > (CustomGameSettings.Current?.PlayerLimit ?? MinPlayerCount) )
		{
			RemoveBot();
		}

		UpdatePlayerCount();
	}

	void IGameEventHandler<PlayerDisconnectedEvent>.OnGameEvent( PlayerDisconnectedEvent eventArgs )
	{
		// Don't react to bot disconnects - shouldn't happen anyway
		if ( eventArgs.Player.IsBot )
			return;

		// Real player left, check if we need to add bots
		UpdatePlayerCount();
	}

	private void UpdatePlayerCount()
	{
		if ( !HasHostAuthority )
			return;

		// Game events still reach disabled components; a disabled rule (e.g. zombies) must not add bots.
		if ( !Active )
			return;

		// A plant or a late join must not replace teammates killed earlier in this round.
		var mode = GameMode.Instance;
		if ( mode?.Ident == "defuse" && (mode.Get<BombPlantedEventComponent>() is not null || mode.Get<BombDefusedEventHandler>() is not null) )
			return;

		var customGame = CustomGameSettings.Current;
		if ( customGame is { FillWithBots: false } )
			return;

		var targetPlayers = customGame?.PlayerLimit ?? MinPlayerCount;
		var teamSize = customGame is null ? MaxTeamSize : Math.Max( 1, targetPlayers / 2 );

		if ( UseLightweightNpcBots )
		{
			GetLightweightBotManager()?.Maintain( targetPlayers, teamSize );
			return;
		}

		var playerCount = GameUtils.AllPlayers.Count();
		var botsNeeded = targetPlayers - playerCount;

		// Add bots if we're below minimum
		while ( botsNeeded > 0 )
		{
			var bot = AddBot();
			if ( bot is null )
				break;

			_addedBots.Add( bot );
			botsNeeded--;
		}
	}

	internal void RestartDefuseRound()
	{
		if ( !HasHostAuthority || GameMode.Instance?.Ident != "defuse" ) return;
		if ( UseLightweightNpcBots ) GetLightweightBotManager()?.ClearBots();
		// Let the previous pawns and bots finish destroying before counting the new roster.
		_timeSinceDefuseReset = 0;
		_defuseRoundFillPending = true;
	}

	private Client AddBot()
	{
		var botManager = BotManager.Instance;
		if ( !botManager.IsValid() )
		{
			botManager = Scene.GetAllComponents<BotManager>().FirstOrDefault();
		}

		if ( !botManager.IsValid() )
			return null;

		// Create bot
		var bot = botManager.AddBot();

		return bot;
	}

	private LightweightBotManager GetLightweightBotManager()
	{
		var manager = LightweightBotManager.Instance;
		if ( manager.IsValid() )
			return manager;

		manager = Scene.GetAllComponents<LightweightBotManager>().FirstOrDefault();
		if ( manager.IsValid() )
			return manager;

		var obj = new GameObject( true, "Lightweight Bot Manager" );
		obj.Flags |= GameObjectFlags.NotSaved;
		manager = obj.AddComponent<LightweightBotManager>();

		if ( Networking.IsActive )
		{
			obj.NetworkSpawn( true, null );
		}

		return manager;
	}

	private void RemoveBot()
	{
		// Remove the last added bot
		var lastBot = _addedBots.LastOrDefault();
		if ( !lastBot.IsValid() )
		{
			lastBot = GameUtils.AllPlayers.LastOrDefault( x => x.IsBot );
		}

		if ( lastBot.IsValid() )
		{
			_addedBots.Remove( lastBot );
			lastBot.Kick( "Making room for player" );
		}
	}

	private void RespawnDeadBots()
	{
		if ( !HasHostAuthority )
			return;

		// Respawn all dead bots that we added
		foreach ( var bot in _addedBots.ToArray() )
		{
			if ( bot.IsValid() && (!bot.PlayerPawn.IsValid() || bot.PlayerPawn.HealthComponent.State != LifeState.Alive) )
			{
				bot.Respawn( forceNew: false );
			}
		}
	}

	protected override void OnDisabled()
	{
		if ( UseLightweightNpcBots )
		{
			var manager = LightweightBotManager.Instance;
			if ( !manager.IsValid() )
			{
				manager = Scene.GetAllComponents<LightweightBotManager>().FirstOrDefault();
			}

			manager?.ClearBots();
		}

		// Clean up any bots we added when disabled
		foreach ( var bot in _addedBots.ToArray() )
		{
			if ( bot.IsValid() )
			{
				bot.Kick( "Rule disabled" );
			}
		}
		_addedBots.Clear();
	}
}
