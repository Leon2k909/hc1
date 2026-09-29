using System.Threading.Tasks;

namespace Facepunch;

/// <summary> Who can join the player's squad (the Steam party). </summary>
public enum SquadPrivacyMode
{
	/// <summary> Listed in s&amp;box's party browser, where anyone can join. Squads were all like this before the setting. </summary>
	Open,

	/// <summary> Unlisted, so only invited players can join. s&amp;box's own menu makes its parties like this. </summary>
	InviteOnly,

	/// <summary> Closed: the squad's MaxMembers is held at its size, so nobody can join. </summary>
	Private,
}

/// <summary>
/// The squad privacy setting (the cog on the hub's squad card), applied to the Steam party (<see cref="PartyRoom"/>).
/// s&amp;box takes a party's listing only when it's made (<c>PartyRoom.Create</c>'s <c>ispublic</c>), so Open and Invite
/// Only apply to new squads, and a squad of one is made again at once. Private works on any squad the player leads, by
/// holding MaxMembers at the squad's size. The setting is the player's own and only applies while they lead.
/// </summary>
public static class SquadPrivacy
{
	private const string Cookie = "hc1.party.privacy";

	/// <summary> The size squads are made with. </summary>
	public const int SquadLimit = 8;

	/// <summary> The squad this game made, and whether it was listed. Other squads' listing isn't known. </summary>
	private static PartyRoom _made;
	private static bool _madeListed;

	/// <summary> The squad's MaxMembers before Private closed it; 0 while it's open. </summary>
	private static int _openLimit;

	private static RealTimeSince _sinceEnforced = 1f;

	// Read every frame by the hub's BuildHash, so the cookie is read once.
	private static SquadPrivacyMode? _mode;

	public static SquadPrivacyMode Mode
	{
		get
		{
			if ( _mode is { } mode ) return mode;

			var value = Game.Cookies.Get<int>( Cookie, 0 );
			_mode = value is >= 0 and <= (int)SquadPrivacyMode.Private ? (SquadPrivacyMode)value : SquadPrivacyMode.Open;
			return _mode.Value;
		}
	}

	public static PartyRoom Party
	{
		get
		{
			try { return PartyRoom.Current; }
			catch { return null; }
		}
	}

	/// <summary> The local player leads their squad, or isn't in one, so the setting is theirs to change. </summary>
	public static bool CanChange
	{
		get
		{
			var party = Party;
			if ( party is null ) return true;

			try { return party.Owner.IsMe; }
			catch { return false; }
		}
	}

	/// <summary> The squad's size limit to show: the open one, not the closed one while it's Private. </summary>
	public static int Limit( PartyRoom party )
	{
		if ( party is null ) return SquadLimit;
		if ( _openLimit > 0 ) return _openLimit;

		try { return party.MaxMembers; }
		catch { return SquadLimit; }
	}

	/// <summary> Open or Invite Only was picked for a squad that was made the other way and that others are in. </summary>
	public static bool AppliesToNextSquad
	{
		get
		{
			var party = Party;
			if ( party is null || Mode == SquadPrivacyMode.Private || !ReferenceEquals( party, _made ) ) return false;

			try { return party.MemberCount > 1 && _madeListed != (Mode == SquadPrivacyMode.Open); }
			catch { return false; }
		}
	}

	/// <summary> Makes a squad with the current setting (see <c>PartyPanel.InviteFriends</c>). </summary>
	public static async Task<PartyRoom> CreateParty()
	{
		var listed = Mode == SquadPrivacyMode.Open;
		var party = await PartyRoom.Create( SquadLimit, "My Party", listed );

		_made = party;
		_madeListed = listed;
		_openLimit = 0;
		Enforce( true );

		return party;
	}

	public static void Set( SquadPrivacyMode mode )
	{
		if ( mode == Mode || !CanChange ) return;

		Game.Cookies.Set( Cookie, (int)mode );
		_mode = mode;

		var party = Party;
		if ( party is not null && mode != SquadPrivacyMode.Private && NeedsRemaking( party ) )
		{
			_ = Remake( party );
			return;
		}

		Enforce( true );
	}

	/// <summary> A squad of one whose listing doesn't match the setting, or isn't known. </summary>
	private static bool NeedsRemaking( PartyRoom party )
	{
		try
		{
			if ( party.MemberCount > 1 ) return false;
			return !ReferenceEquals( party, _made ) || _madeListed != (Mode == SquadPrivacyMode.Open);
		}
		catch
		{
			return false;
		}
	}

	private static async Task Remake( PartyRoom party )
	{
		try { party.Leave(); }
		catch { }

		_made = null;
		await CreateParty();
	}

	/// <summary>
	/// Keeps a Private squad closed as people leave (MaxMembers follows its size), and opens it again when the setting
	/// changes or when the player takes over a squad a Private leader closed. Only the leader can set MaxMembers.
	/// Runs every half second at most, from the hub's sidebar and <see cref="SquadSocialSystem"/>.
	/// </summary>
	public static void Enforce( bool now = false )
	{
		if ( !now && _sinceEnforced < 0.5f ) return;
		_sinceEnforced = 0;

		var party = Party;
		if ( party is null )
		{
			_openLimit = 0;
			return;
		}

		try
		{
			if ( !party.Owner.IsMe ) return;

			var size = Math.Max( 1, party.MemberCount );
			if ( Mode == SquadPrivacyMode.Private )
			{
				if ( party.MaxMembers == size ) return;
				if ( _openLimit == 0 ) _openLimit = party.MaxMembers;
				party.MaxMembers = size;
			}
			else if ( _openLimit > 0 || (party.MaxMembers <= size && size < SquadLimit) )
			{
				party.MaxMembers = Math.Max( _openLimit > 0 ? _openLimit : SquadLimit, size );
				_openLimit = 0;
			}
		}
		catch
		{
			// Steam can drop the party mid-read.
		}
	}
}
