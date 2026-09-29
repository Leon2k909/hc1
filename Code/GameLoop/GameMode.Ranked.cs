using Facepunch.UI;
using System.Threading.Tasks;

namespace Facepunch;

partial class GameMode
{
	public static bool ActiveRanked { get; private set; }
	[Sync( SyncFlags.FromHost )] public bool IsRanked { get; private set; }
	private string _rankedMatchId;
	private bool _rankedResultSent;

	/// <summary>Prepare the next match after selecting its mode. Ordinary mode selection clears this flag.</summary>
	public static void PrepareRankedMatch() => ActiveRanked = true;

	private void InitializeRankedMatch()
	{
		IsRanked = ActiveRanked;
		_rankedMatchId = Guid.NewGuid().ToString();
		_rankedResultSent = false;
	}

	/// <summary>Only the host can complete a ranked match and send each participant their own result.</summary>
	public bool FinishRankedMatch( Team winner )
	{
		if ( !IsRanked || !Networking.IsHost ) return false;
		if ( _rankedResultSent ) return true;
		_rankedResultSent = true;
		Networking.SetData( "ranked_closed", "1" );

		var players = GameUtils.AllPlayers.Where( x => x.IsValid() && x.IsConnected && x.Team != Team.Unassigned ).ToList();
		foreach ( var player in players.Where( x => !x.IsBot && x.Connection is not null ) )
		{
			var score = Math.Max( 0, player.GetComponent<PlayerScore>()?.Score ?? 0 );
			var scores = players.Where( x => x.Team == player.Team )
				.Select( x => (float)Math.Max( 0, x.GetComponent<PlayerScore>()?.Score ?? 0 ) )
				.Concat( GameUtils.LightweightBots.Where( x => x.IsValid() && x.Team == player.Team ).Select( x => (float)Math.Max( 0, x.Score ) ) )
				.ToList();
			var average = scores.Count > 0 ? scores.Average() : 0f;
			var performance = average > 0f ? Math.Clamp( score / (average * 2f), 0f, 1f ) : 0f;
			using ( Rpc.FilterInclude( player.Connection ) )
				ReceiveRankedResult( _rankedMatchId, winner == player.Team, winner == Team.Unassigned, performance );
		}

		ReturnToRankedAfterMatch();
		return true;
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void ReceiveRankedResult( string matchId, bool won, bool draw, float performance )
	{
		Rank.RecordResult( matchId, won, draw, performance );
	}

	// Everyone receives the timer before the host disconnects. A fresh search uses each player's updated tier.
	[Rpc.Broadcast( NetFlags.HostOnly )]
	private async void ReturnToRankedAfterMatch()
	{
		var matchScene = Scene;
		await Task.Delay( 15000 );
		if ( !IsValid || Game.ActiveScene != matchScene || !Networking.IsActive ) return;
		Networking.Disconnect();
		GameUtils.ReturnToMainMenu( "/ranked" );
	}
}
