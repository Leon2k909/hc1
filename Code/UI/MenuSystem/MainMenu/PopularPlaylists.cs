using System.Threading.Tasks;

namespace Facepunch.UI;

/// <summary>
/// The hub's Popular Playlists row, under the featured Multiplayer screen: the Quick Play modes, most played first. How
/// many players have won a match in each mode (the global "wins-&lt;ident&gt;" stat, which <see cref="StatIncrementer"/>
/// sends in the modes with SendExtraGameModeStat) ranks them. Modes that don't send it, or that nobody has won yet, keep
/// the curated order, and so does everything in the editor, where global stats read 0.
/// </summary>
public static class PopularPlaylists
{
	/// <summary>The usual order, with the core team modes first.</summary>
	private static readonly string[] Curated =
	{
		"tdm", "domination", "hardpoint", "defuse", "gunfight_2v2", "dm", "gun_game", "retakes", "cashgrab", "gunfight_1v1"
	};

	/// <summary>The card's subtitle: players a side, then the mode in a few words (from its description). A mode that
	/// isn't here shows how many maps it's on. In English: <see cref="Subtitle"/> translates it.</summary>
	private static readonly Dictionary<string, string> Subtitles = new( StringComparer.OrdinalIgnoreCase )
	{
		["tdm"] = "5V5 | INSTANT RESPAWNS",
		["domination"] = "5V5 | CAPTURE AND HOLD",
		["hardpoint"] = "5V5 | ROTATING ZONE",
		["defuse"] = "5V5 | NO RESPAWNS",
		["retakes"] = "5V5 | AFTER-PLANT ROUNDS",
		["cashgrab"] = "5V5 | CAPTURE THE CASH",
		["gunfight_1v1"] = "1V1 | INSTANT RESPAWNS",
		["gunfight_2v2"] = "2V2 | INSTANT RESPAWNS",
		["dm"] = "FREE FOR ALL",
		["gun_game"] = "FREE FOR ALL | WEAPON TIERS",
	};

	private static Task _refresh;

	/// <summary>Fetches the global stats, once a session. The task finishes when they've arrived.</summary>
	public static Task RefreshStats()
	{
		try
		{
			return _refresh ??= Sandbox.Services.Stats.Global.Refresh();
		}
		catch ( Exception e )
		{
			Log.Warning( $"Popular playlists: couldn't fetch global stats ({e.Message})" );
			return _refresh = Task.CompletedTask;
		}
	}

	private static long Players( GameMode mode ) =>
		Sandbox.Services.Stats.Global.TryGet( $"wins-{mode.Ident}", out var stat ) ? stat.Players : 0;

	private static int CuratedRank( GameMode mode )
	{
		var i = Array.FindIndex( Curated, x => string.Equals( x, mode.Ident, StringComparison.OrdinalIgnoreCase ) );
		return i < 0 ? Curated.Length : i;
	}

	/// <summary>The top <paramref name="count"/> Quick Play modes, most played first.</summary>
	public static List<GameMode> Top( int count ) => QuickPlayFilter.Modes
		.OrderByDescending( Players )
		.ThenBy( CuratedRank )
		.ThenBy( m => m.Title )
		.Take( count )
		.ToList();

	/// <summary>The card's name, in the player's language. TDM's title is short for the scoreboard; the card has room
	/// for the whole name.</summary>
	public static string Name( GameMode mode ) =>
		string.Equals( mode.Ident, "tdm", StringComparison.OrdinalIgnoreCase ) ? Tr( "TEAM DEATHMATCH" ) : Tr( mode.Title.ToUpper() );

	/// <summary>The card's subtitle, in the player's language.</summary>
	public static string Subtitle( GameMode mode )
	{
		if ( Subtitles.TryGetValue( mode.Ident ?? "", out var subtitle ) ) return Tr( subtitle );

		var maps = QuickPlayFilter.MapsFor( mode ).Count;
		return Tr( maps == 1 ? "{0} MAP" : "{0} MAPS", maps );
	}

	/// <summary>The card's art class: the mode's ident, which HubPage.razor.scss maps to ui/modes/playlists/&lt;ident&gt;.png.</summary>
	public static string ArtClass( GameMode mode ) => mode.Ident?.ToLowerInvariant() ?? "";

	/// <summary>Starts a match in <paramref name="mode"/> on a random map for it (<see cref="PickMap"/>).</summary>
	public static void Play( GameMode mode )
	{
		if ( PickMap( mode ) is { } map )
			MatchLauncher.StartMatch( mode, map );
	}

	/// <summary>
	/// A random map for <paramref name="mode"/>, keeping to the maps ticked in the Quick Play filter if any of them have
	/// it. Null if no match map has the mode.
	/// </summary>
	public static SceneFile PickMap( GameMode mode )
	{
		var maps = QuickPlayFilter.MapsFor( mode );
		if ( maps.Count == 0 ) return null;

		var ticked = maps.Where( QuickPlayFilter.IsIncluded ).ToList();
		return Game.Random.FromList( ticked.Count > 0 ? ticked : maps );
	}
}
