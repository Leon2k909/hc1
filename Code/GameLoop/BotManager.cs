namespace Facepunch;

/// <summary>
/// A singleton component which handles the bots in a game. Gives them funny names.
/// </summary>
public sealed class BotManager : SingletonComponent<BotManager>
{
	private bool HasHostAuthority => !IsProxy || Networking.IsHost || (Connection.Local?.IsHost ?? false);

	private static readonly string[] BotNames =
	{
		"Gordon",
		"Jamie",
		"Nigella",
		"Heston",
		"Anthony",
		"Ainsley",
		"Delia",
		"Loyd",
		"Paul",
		"Marco"
	};
	public string[] Names;

	[Sync( SyncFlags.FromHost )] private int CurrentBotId { get; set; } = 0;

	protected override void OnAwake()
	{
		base.OnAwake();

		Names = BotNames.Shuffle().ToArray();
	}

	public Client AddBot()
	{
		if ( !HasHostAuthority )
		{
			Log.Warning( "Could not add bot: no host authority." );
			return null;
		}

		var networkManager = GameNetworkManager.Instance;
		if ( !networkManager.IsValid() )
		{
			networkManager = Scene.GetAllComponents<GameNetworkManager>().FirstOrDefault();
		}

		if ( !networkManager.IsValid() )
		{
			Log.Warning( "Could not add bot: no GameNetworkManager found." );
			return null;
		}

		if ( !networkManager.ClientPrefab.IsValid() )
		{
			Log.Warning( "Could not add bot: GameNetworkManager has no valid ClientPrefab." );
			return null;
		}

		var player = networkManager.ClientPrefab.Clone();
		player.BreakFromPrefab();
		player.Flags |= GameObjectFlags.NotSaved;
		player.Network.SetOrphanedMode( NetworkOrphaned.ClearOwner );
		player.Name = $"Client (BOT)";

		// AI
		player.AddComponent<BotController>();

		var client = player.GetComponent<Client>();
		if ( !client.IsValid() )
		{
			Log.Warning( "Could not add bot: ClientPrefab has no Client component." );
			player.Destroy();
			return null;
		}

		client.BotId = CurrentBotId;

		// Simpsons
		var steamid = Game.Random.FromArray( [
				76561198076731362,
				76561198115447501,
				76561198081295106,
				76561198165412225,
				76561198023414915,
				76561198176366622,
				76561198092430664,
				76561198066084037,
				76561198368894435,
				76561198389241377,
				76561198158965172,
				76561198306626714,
				76561198208716648,
				76561198835780877,
				76561197970331648,
				76561198051740093,
				76561198111069943,
				76561198075423731,
				76561197965588718,
				76561197960316241,
				76561198361294115,
				76561197960555384,
				76561198021354850,
				76561198207495888,
				76561198040673812,
				76561198241363850,
				76561198151921867,
				76561198095212046,
				76561198169445087
		] );

		client.SteamId = (ulong)steamid;

		networkManager.OnPlayerJoined( client, null );

		if ( client.Team != Team.Unassigned && !client.PlayerPawn.IsValid() )
		{
			client.RespawnState = RespawnState.Immediate;
			client.Respawn( true );
		}

		CurrentBotId++;

		return client;
	}

	public string GetName( int id )
	{
		Names ??= BotNames;
		return Names[id % Names.Length];
	}

	[DeveloperCommand( "Add Bot", "Game Loop" )]
	private static void Command_Add_Bot()
	{
		GetActiveManager()?.AddBot();
	}

	[DeveloperCommand( "Add 9 Bots", "Game Loop" )]
	private static void Command_Add_Bots_Filled()
	{
		var manager = GetActiveManager();
		if ( !manager.IsValid() )
			return;

		for ( int i = 0; i < 9; i++ )
		{
			manager.AddBot();
		}
	}

	private static BotManager GetActiveManager()
	{
		if ( Instance.IsValid() )
			return Instance;

		return Game.ActiveScene?.GetAllComponents<BotManager>().FirstOrDefault();
	}

	[DeveloperCommand( "Kick all Bots", "Game Loop" )]
	private static void Command_Kick_Bots()
	{
		foreach ( var player in GameUtils.AllPlayers )
		{
			if ( player.IsBot )
			{
				player.Kick();
			}
		}
	}
}
