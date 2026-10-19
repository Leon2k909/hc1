using Sandbox;
using Sandbox.Events;

namespace Facepunch;

public partial class Client : Component, ITeam, IGameEventHandler<KillEvent>
{
	/// <summary>
	/// The player we're currently in the view of (clientside).
	/// Usually the local player, apart from when spectating etc.
	/// </summary>
	public static Client Viewer { get; private set; }

	/// <summary>
	/// Our local player on this client.
	/// </summary>
	public static Client Local { get; private set; }

	// --

	/// <summary>
	/// Who owns this player state?
	/// </summary>
	[Sync( SyncFlags.FromHost ), Property] public ulong SteamId { get; set; }

	/// <summary>
	/// The player's name, which might have to persist if they leave
	/// </summary>
	[Sync( SyncFlags.FromHost )] public string SteamName { get; set; }

	/// <summary>
	/// The player's clan tag
	/// </summary>
	[Sync( SyncFlags.FromHost )] public string ClanTag { get; set; }

	/// <summary>
	/// Custom Emblem data synced over the network
	/// </summary>
	[Sync( SyncFlags.FromHost )] public string EmblemDataJson { get; set; }

	[Rpc.Broadcast]
	public void RpcUpdateEmblem( string json )
	{
		if ( Rpc.Caller != Connection ) return;
		EmblemDataJson = json;
	}

	/// <summary>
	/// Custom Prestige level synced over the network
	/// </summary>
	[Sync( SyncFlags.FromHost )] public int PrestigeLevel { get; set; }

	[Rpc.Broadcast]
	public void RpcUpdatePrestige( int prestige )
	{
		if ( Rpc.Caller != Connection ) return;
		PrestigeLevel = prestige;
	}

	/// <summary>
	/// The connection of this player
	/// </summary>
	public Connection Connection => Network.Owner;

	/// <summary>
	/// Is this player connected? Clients can linger around in competitive matches to keep a player's slot in a team if they disconnect.
	/// </summary>
	public bool IsConnected => IsBot || Connection is not null && (Connection.IsActive || Connection.IsHost); //smh

	private string name => IsBot ? $"BOT {(BotManager.Instance?.GetName( BotId ) ?? $"Bot {BotId}")}" : SteamName ?? "";
	/// <summary>
	/// Name of this player
	/// </summary>
	public string DisplayName => $"{(string.IsNullOrWhiteSpace(ClanTag) ? "" : $"[{ClanTag}] ")}{name}{(!IsConnected ? " (Disconnected)" : "")}";

	/// <summary>
	/// What's our loadout?
	/// </summary>
	[RequireComponent] public PlayerLoadout Loadout { get; private set; }

	/// <summary>
	/// The team this player is on.
	/// </summary>
	[Property, Group( "Setup" ), Sync( SyncFlags.FromHost ), Change( nameof( OnTeamPropertyChanged ) )]

	public Team Team { get; set; }

	/// <summary>
	/// Are we in the view of this player (clientside)
	/// </summary>
	public bool IsViewer => Viewer == this;

	/// <summary>
	/// Is this the local player for this client
	/// </summary>
	public bool IsLocalPlayer => !IsProxy && !IsBot && Connection == Connection.Local;

	/// <summary>
	/// Unique colour or team color of this player
	/// </summary>
	public Color PlayerColor => Team.GetColor();

	/// <summary>
	/// The main PlayerPawn of this player if one exists, will not change when the player possesses gadgets etc. (synced)
	/// </summary>
	[Sync( SyncFlags.FromHost ), ValidOrNull] public PlayerPawn PlayerPawn { get; set; }

	/// <summary>
	/// The pawn this player is currently in possession of (synced - unless the pawn is not networked)
	/// </summary>
	[Sync] public Pawn Pawn { get; set; }

	public void HostInit()
	{
		var defaultRespawnState = Scene.GetAllComponents<DefaultRespawnState>().FirstOrDefault();
		if ( defaultRespawnState.IsValid() )
		{
			RespawnState = defaultRespawnState.RespawnState;
		}
		else
		{
			// on join, spawn right now if we can
			RespawnState = RespawnState.Delayed;
		}

		if ( !IsBot )
		{
			SteamId = Connection.SteamId;
			SteamName = Connection.DisplayName;
		}
		else
		{
			SteamName = Connection?.DisplayName ?? $"Bot {BotId}";
		}
	}

	[Rpc.Owner]
	public void ClientInit()
	{
		if ( IsBot )
			return;

		Local = this;
		InitializeTrainingOnOwner();
		
		// Send our local prestige to everyone else
		RpcUpdatePrestige( Progression.GetPrestigeEmblem() );
	}

	[Rpc.Host]
	public void UpdateClanTag( string tag )
	{
		ClanTag = tag;
	}

	/// <summary>
	/// The outfits this player equipped on the Operators page, one id per team (<see cref="OperatorOutfits.LocalPicks"/>).
	/// The host dresses their body from it (<see cref="HumanOutfitter"/>).
	/// </summary>
	[Sync( SyncFlags.FromHost ), Change( nameof( OnOperatorPicksChanged ) )] public string OperatorPicks { get; set; }

	[Rpc.Host]
	public void UpdateOperatorPicks( string picks )
	{
		OperatorPicks = picks?.Truncate( 128 );
	}

	/// <summary>
	/// Picks that come in after the player spawned (they're sent once the client is up) dress the body they have. A dead
	/// player's are put on at the respawn.
	/// </summary>
	private void OnOperatorPicksChanged( string before, string after )
	{
		if ( !Networking.IsHost || !PlayerPawn.IsValid() || PlayerPawn.HealthComponent?.State != LifeState.Alive )
			return;

		foreach ( var outfitter in PlayerPawn.GetComponentsInChildren<HumanOutfitter>( true ) )
			outfitter.UpdateFromTeam( PlayerPawn.Team );
	}

	public void Kick( string reason = "No reason" )
	{
		if ( PlayerPawn.IsValid() )
		{
			PlayerPawn.GameObject.Destroy();
		}

		GameObject.Destroy();

		// Don't kick our owner
		if ( IsBot )
			return;

		// Kick the client
		Network.Owner.Kick( reason );
	}

	public static void OnPossess( Pawn pawn )
	{
		if ( !pawn.IsValid() )
		{
			Log.Warning( "Tried to possess an invalid pawn." );
			return;
		}

		if ( !Local.IsValid() )
		{
			Log.Warning( "Tried to possess a pawn but we don't have a local Client" );
			return;
		}

		// called from Pawn when one is newly possessed, update Local and Viewer, invoke RPCs for observers

		Local.Pawn = pawn;

		if ( pawn.Network.Active )
		{
			Local.OnNetPossessed();
		}

		if ( !pawn.Client.IsValid() )
		{
			Log.Warning( $"Attempted to possess pawn, but pawn '{pawn.DisplayName}' has no attached Client! Using Local." );
			Viewer = Local;
			return;
		}

		Viewer = pawn.Client;
	}

	// sync to other clients what this player is currently possessing
	// Sol: when we track observers we could drop this with an Rpc.FilterInclude?
	[Rpc.Broadcast]
	private void OnNetPossessed()
	{
		if ( IsViewer && IsProxy )
		{
			Possess();
		}
	}

	public void Possess()
	{
		if ( Pawn is null || IsLocalPlayer )
		{
			if ( PlayerPawn.IsValid() )
			{
				// Local player - always assume the controller
				PlayerPawn.Possess();
			}
		}
		else
		{
			// A remote player is possessing this player (spectating)
			// So enter the latest known pawn this player has possessed
			Pawn.Possess();
		}
	}

	public void AssignTeam( Team team )
	{
		if ( !Networking.IsHost )
			return;

		Team = team;

		Scene.Dispatch( new TeamAssignedEvent( this, team ) );
	}

	[Rpc.Host]
	public void RequestTeam( Team team )
	{
		AssignTeam( team );
	}

	/// <summary>
	/// Called when <see cref="Team"/> changes across the network.
	/// </summary>
	private void OnTeamPropertyChanged( Team before, Team after )
	{
		GameObject.Root.Dispatch( new TeamChangedEvent( before, after ) );

		// Send this to the pawn too if we have ne
		if ( PlayerPawn.IsValid() )
		{
			PlayerPawn.GameObject.Root.Dispatch( new TeamChangedEvent( before, after ) );
		}
	}

	private Client deathCommKiller;
	private RealTimeSince timeSinceDeathComm;

	public void StartDeathComm( Client killer )
	{
		deathCommKiller = killer;
		timeSinceDeathComm = 0;
	}

	public bool HasActiveDeathCommTo( Client killer )
	{
		return deathCommKiller == killer && timeSinceDeathComm < 2.5f;
	}

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		if ( !GameSettingsSystem.Current.VoiceDeathComms )
			return;

		var attacker = eventArgs.DamageInfo.Attacker;
		var victim = eventArgs.DamageInfo.Victim;

		Client attackerClient = null;
		if ( attacker is Client c ) attackerClient = c;
		else if ( attacker is PlayerPawn p ) attackerClient = p.Client;

		Client victimClient = null;
		if ( victim is Client vc ) victimClient = vc;
		else if ( victim is PlayerPawn vp ) victimClient = vp.Client;

		if ( attackerClient.IsValid() && victimClient.IsValid() && attackerClient != victimClient )
		{
			if ( victimClient == this )
			{
				StartDeathComm( attackerClient );
			}
		}
	}
}
