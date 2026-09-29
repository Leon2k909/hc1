using Facepunch.UI;
using Sandbox.Diagnostics;

namespace Facepunch;

[Hide]
public partial class MapVoteSystem : SingletonComponent<MapVoteSystem>
{
	/// <summary>
	/// Our networked list of voting options.
	/// </summary>
	[Sync] private NetList<NetworkedOption> Options { get; set; } = new();

	/// <summary>
	/// Our networked list of votes.
	/// </summary>
	[Sync] public NetList<NetworkedVote> Votes { get; set; } = new();

	/// <summary>
	/// How long the vote stays open, in seconds.
	/// </summary>
	public const float VoteDuration = 15f;

	/// <summary>
	/// How long until we decide who won?
	/// </summary>
	public RealTimeUntil TimeUntilDecidedWinner { get; private set; } = 0;

	/// <summary>
	/// How long until we move server?
	/// </summary>
	public RealTimeUntil TimeUntilTransfer { get; private set; } = 0;

	/// <summary>
	/// Which option is the winner?
	/// </summary>
	public Option? WinningOption { get; private set; }

	/// <summary>
	/// The winning option's index once the vote's decided, -1 before. Synced so every client's cards show it.
	/// </summary>
	[Sync] public int WinnerIndex { get; set; } = -1;

	/// <summary>
	/// Set on this machine while its player leaves for another mode (<see cref="MapVoteOverlay"/>): until it's cleared,
	/// the vote moves nobody on from here. Once the lobby's gone, a client's copy would otherwise run the host's side and
	/// load the winning map over the new mode's. Cleared again if the player couldn't leave.
	/// </summary>
	public bool IsLeaving { get; set; }

	public IEnumerable<Option> VoteOptions => FromNetworked( Options );

	public int OptionCount => Options.Count;

	/// <summary>
	/// An instance of the map vote overlay UI
	/// </summary>
	[RequireComponent] MapVoteOverlay MapVoteOverlay { get; set; }

	/// <summary>
	/// The screen panel which draws our UI
	/// </summary>
	[RequireComponent] ScreenPanel ScreenPanel { get; set; }

	protected override void OnAwake()
	{
		base.OnAwake();

		TimeUntilDecidedWinner = VoteDuration;
		ScreenPanel.ZIndex = 999;
	}

	protected override void OnUpdate()
	{
		if ( IsProxy || IsLeaving )
			return;

		if ( TimeUntilDecidedWinner && WinningOption is null )
		{
			TimeUntilTransfer = 5;

			if ( Options.Count == 0 )
			{
				GameUtils.ReturnToMainMenu();
				return;
			}

			WinnerIndex = PickWinner();
			WinningOption = GetOption( WinnerIndex );
		}

		if ( WinningOption.HasValue && TimeUntilTransfer )
		{
			var option = WinningOption.Value;
			GameMode.SetCurrent( option.Mode );
			Game.ActiveScene.Load( option.Map );
		}
	}

	/// <summary>
	/// Converts a list of networked options to readable ones
	/// </summary>
	/// <param name="networked"></param>
	/// <returns></returns>
	private static IEnumerable<Option> FromNetworked( IEnumerable<NetworkedOption> networked )
	{
		return networked.Select( x => x.AsNormal() );
	}

	/// <summary>
	/// Converts a list of normal options to networked ones
	/// </summary>
	/// <param name="normal"></param>
	/// <returns></returns>
	private static IEnumerable<NetworkedOption> ToNetworked( IEnumerable<Option> normal )
	{
		return normal.Select( x => x.AsNetworked() );
	}

	private Option GetOption( int index )
	{
		return Options[index].AsNormal();
	}

	/// <summary>
	/// How many votes an option has.
	/// </summary>
	public int GetVoteCount( int index ) => Votes.Count( x => x is not null && x.Option == index );

	/// <summary>
	/// The option with the most votes. A tie, or no votes at all, is settled at random between the leaders.
	/// </summary>
	private int PickWinner()
	{
		var counts = Enumerable.Range( 0, Options.Count ).Select( GetVoteCount ).ToList();
		var most = counts.Max();

		return Game.Random.FromList( Enumerable.Range( 0, Options.Count ).Where( i => counts[i] == most ).ToList() );
	}

	/// <summary>
	/// One option per match map, in a random order, each in the mode that was just played (or a random mode the map
	/// has, if it doesn't have that one). Players vote on the map; the mode stays what the lobby picked. This used to
	/// pick maps at random with repeats and a different mode for each, so two maps filled five cards with duplicates.
	/// </summary>
	public static IEnumerable<Option> GenerateOptions( GameMode currentMode = null, SceneFile currentMap = null, int count = 5 )
	{
		currentMode ??= GameMode.Instance;
		var options = new List<Option>();

		foreach ( var map in GameUtils.GetMatchMaps().OrderBy( _ => Game.Random.Float() ).Take( count ) )
		{
			var modes = GameMode.GetAll( map ).ToList();
			var mode = modes.FirstOrDefault( x => currentMode.IsValid() && x.Ident == currentMode.Ident ) ?? Game.Random.FromList( modes );

			if ( mode is not null )
				options.Add( new Option { Map = map, Mode = mode } );
		}

		return options;
	}

	/// <summary>
	/// Start a vote. This'll make a component on the server and 
	/// </summary>
	/// <param name="currentMode"></param>
	/// <param name="currentMap"></param>
	/// <param name="count"></param>
	/// <returns></returns>
	public static MapVoteSystem Create( GameMode currentMode = null, SceneFile currentMap = null, int count = 5 )
	{
		// Host-only
		Assert.True( Networking.IsHost );

		if ( Instance.IsValid() )
		{
			Instance.GameObject.Destroy();
		}

		var generated = GenerateOptions( currentMode, currentMap, count )
			.ToList();

		// Push the active scene
		using var _ = Game.ActiveScene.Push();

		var go = new GameObject();
		var system = go.Components.Create<MapVoteSystem>();

		// Add our generated options to the NetList so it's sent to clients
		foreach ( var option in ToNetworked( generated ) )
		{
			system.Options.Add( option );
		}

		// Spawn this object over the network
		go.NetworkSpawn();

		return system;
	}

	/// <summary>
	/// TODO: remove me
	/// </summary>
	[ConCmd( "hc1_dev_mapvote" )]
	public static void Dev_CreateMapVote()
	{
		Create();
	}

	/// <summary>
	/// RPCs a vote, targeted to the host, so it's not exposed to any public API.
	/// </summary>
	/// <param name="index"></param>
	[Rpc.Broadcast]
	private void RpcVote( int index )
	{
		var callerSteamId = Rpc.Caller.SteamId;
		if ( index < 0 || index >= Options.Count )
			return;

		// did we already get a winning option?
		if ( WinningOption is { } option )
			return;

		Log.Info( $"{callerSteamId} trying to vote for index {index}" );

		var existingVote = Votes.FirstOrDefault( x => x is not null && x.VoterId == callerSteamId );
		if ( existingVote is not null )
		{
			Votes.Remove( existingVote );
		}

		// Don't re-add if we vote for the same thing
		if ( existingVote is not null && existingVote.Option == index ) return;

		Votes.Add( new NetworkedVote()
		{
			Option = index,
			VoterId = callerSteamId,
		} );
	}

	/// <summary>
	/// Sends a vote to the host.
	/// </summary>
	/// <param name="index"></param>
	public void Vote( int index )
	{
		using ( Rpc.FilterInclude( Connection.Host ) )
		{
			RpcVote( index );
		}
	}

	/// <summary>
	/// A networked vote.
	/// </summary>
	public class NetworkedVote
	{
		/// <summary>
		/// The player's SteamId
		/// </summary>
		public ulong VoterId { get; set; }

		/// <summary>
		/// Which option are we voting for? (Mapped to the list)
		/// </summary>
		public int Option { get; set; }
	}

	/// <summary>
	/// A voting option that has real data.
	/// </summary>
	public record struct Option
	{
		/// <summary>
		/// What mode are we playing?
		/// </summary>
		public GameMode Mode { get; set; }

		/// <summary>
		/// What map?
		/// </summary>
		public SceneFile Map { get; set; }

		/// <summary>
		/// Converts this to a networkable <see cref="NetworkedOption"/>
		/// </summary>
		/// <returns></returns>
		public NetworkedOption AsNetworked()
		{
			// GetPrefabPath, not PrefabInstanceSource: the modes are the prefabs' own GameModes, which have no instance
			// source, so every option used to come back as the map's first mode (TDM).
			return new NetworkedOption
			{
				ModeResource = GameMode.GetPrefabPath( Mode ),
				MapResource = Map.ResourcePath
			};
		}

		public override string ToString()
		{
			return $"{Mode}, {Map}";
		}
	}

	/// <summary>
	/// A networkable variant of <see cref="Option"/>, since it only passes through strings.
	/// </summary>
	public struct NetworkedOption
	{
		/// <summary>
		/// The full resource path of the map.
		/// </summary>
		public string MapResource { get; set; }

		/// <summary>
		/// The full resource path of the gamemode.
		/// </summary>
		public string ModeResource { get; set; }

		/// <summary>
		/// Convert this to a readable <see cref="Option"/>
		/// </summary>
		/// <returns></returns>
		public Option AsNormal()
		{
			var mapDef = ResourceLibrary.Get<SceneFile>( MapResource );
			var modePath = ModeResource;
			var mode = GameMode.GetAll( mapDef )
				.FirstOrDefault( x => GameMode.GetPrefabPath( x ) == modePath );

			return new Option
			{
				Map = mapDef,
				Mode = mode
			};
		}

		public override string ToString()
		{
			return $"{MapResource}, {ModeResource}";
		}
	}
}
