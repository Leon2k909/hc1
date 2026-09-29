namespace Facepunch;

/// <summary>
/// Steam friends the player has been in a match or a squad with, for the hub's FRIENDS card. A game can't read the Steam
/// friends list: s&amp;box's menu has it (<c>MenuUtility.Friends</c>), but that's in Sandbox.Menu, which games don't
/// reference. So the card lists the friends the game has met, with their live status (<see cref="Friend"/>), and its
/// ALL FRIENDS row opens s&amp;box's own list.
/// </summary>
public static class RecentFriends
{
	private const string Cookie = "hc1.friends.recent";
	private const int MaxRemembered = 20;

	/// <summary> A remembered friend: their Steam id and when they were last seen (unix seconds). </summary>
	public readonly record struct Entry( ulong SteamId, long LastSeen );

	private static List<Entry> _entries;
	private static RealTimeSince _sinceScan = 10f;

	/// <summary> Goes up on every change, for BuildHash. </summary>
	public static int Version { get; private set; }

	/// <summary> Newest first. </summary>
	public static IEnumerable<Entry> All => (_entries ??= Load()).OrderByDescending( x => x.LastSeen );

	/// <summary> Remembers the Steam friends in this match and in the squad. Every few seconds at most. </summary>
	public static void Scan()
	{
		if ( _sinceScan < 5f ) return;
		_sinceScan = 0;

		try
		{
			foreach ( var connection in Connection.All )
			{
				if ( connection is null || connection == Connection.Local ) continue;

				var id = (ulong)connection.SteamId;
				if ( id != 0 && new Friend( id ).IsFriend ) Remember( id );
			}

			var party = PartyRoom.Current;
			if ( party is null ) return;

			foreach ( var member in party.Members )
			{
				if ( !member.IsMe && member.IsFriend ) Remember( member.Id );
			}
		}
		catch
		{
			// Steam can drop the party mid-read.
		}
	}

	public static void Remember( ulong steamId )
	{
		if ( steamId == 0 ) return;
		_entries ??= Load();

		var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
		var index = _entries.FindIndex( x => x.SteamId == steamId );

		// Saved at most once a minute per friend while they're around.
		if ( index >= 0 && now - _entries[index].LastSeen < 60 ) return;

		if ( index >= 0 ) _entries[index] = new Entry( steamId, now );
		else _entries.Add( new Entry( steamId, now ) );

		if ( _entries.Count > MaxRemembered )
		{
			_entries = _entries.OrderByDescending( x => x.LastSeen ).Take( MaxRemembered ).ToList();
		}

		Save();
	}

	/// <summary> Whether the friend is on the card. </summary>
	public static bool Contains( ulong steamId ) => (_entries ??= Load()).Any( x => x.SteamId == steamId );

	public static void Forget( ulong steamId )
	{
		_entries ??= Load();
		if ( _entries.RemoveAll( x => x.SteamId == steamId ) > 0 ) Save();
	}

	public static void Clear()
	{
		_entries = new List<Entry>();
		Save();
	}

	private static List<Entry> Load()
	{
		var entries = new List<Entry>();
		foreach ( var part in (Game.Cookies.Get<string>( Cookie, "" ) ?? "").Split( ';', StringSplitOptions.RemoveEmptyEntries ) )
		{
			var bits = part.Split( ':' );
			if ( bits.Length == 2 && ulong.TryParse( bits[0], out var id ) && long.TryParse( bits[1], out var seen ) )
				entries.Add( new Entry( id, seen ) );
		}

		return entries;
	}

	private static void Save()
	{
		Game.Cookies.Set( Cookie, string.Join( ";", _entries.Select( x => $"{x.SteamId}:{x.LastSeen}" ) ) );
		Version++;
	}
}

/// <summary>
/// Squad upkeep in every scene, menu and match: keeps the squad's privacy applied (<see cref="SquadPrivacy.Enforce"/>)
/// and remembers the friends the player meets (<see cref="RecentFriends.Scan"/>). Both throttle themselves.
/// </summary>
public sealed class SquadSocialSystem : GameObjectSystem<SquadSocialSystem>
{
	public SquadSocialSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, 0, Tick, "SquadSocialSystem.Tick" );
	}

	private void Tick()
	{
		SquadPrivacy.Enforce();
		RecentFriends.Scan();
	}
}
