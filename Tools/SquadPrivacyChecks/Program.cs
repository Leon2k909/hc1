global using Sandbox;
using Facepunch;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
PartyRoom Party( int size, int capacity, bool leader = true ) => new()
{
	MemberCount = size, MaxMembers = capacity, Owner = new PartyMember { IsMe = leader }
};

var original = Party( 3, 12 );
PartyRoom.Current = original;
SquadPrivacy.Set( SquadPrivacyMode.Private );
Check( original.MaxMembers == 3 && SquadPrivacy.Limit( original ) == 12, "Private squads must close while displaying their original capacity." );

var next = Party( 2, 6 );
PartyRoom.Current = next;
Check( SquadPrivacy.Limit( next ) == 6, "A different squad must not display the previous squad's cached capacity." );
SquadPrivacy.Enforce( true );
Check( next.MaxMembers == 2 && SquadPrivacy.Limit( next ) == 6, "Private enforcement must remember the new squad's own capacity." );
SquadPrivacy.Set( SquadPrivacyMode.Open );
Check( next.MaxMembers == 6, "Reopening a different squad must restore six slots, not the previous squad's twelve." );

var third = Party( 4, 10 );
PartyRoom.Current = third;
SquadPrivacy.Set( SquadPrivacyMode.Private );
third.MemberCount = 3;
SquadPrivacy.Enforce( true );
Check( third.MaxMembers == 3 && SquadPrivacy.Limit( third ) == 10, "Members leaving a private squad must not overwrite its original capacity." );
SquadPrivacy.Set( SquadPrivacyMode.InviteOnly );
Check( third.MaxMembers == 10, "Invite-only must restore the same squad's original capacity." );

SquadPrivacy.Set( SquadPrivacyMode.Private );
var foreign = Party( 2, 5, leader: false );
PartyRoom.Current = foreign;
Check( SquadPrivacy.Limit( foreign ) == 5, "A non-leader's squad must not display another squad's cached capacity." );
var writes = foreign.CapacityWrites;
SquadPrivacy.Enforce( true );
SquadPrivacy.Set( SquadPrivacyMode.Open );
Check( foreign.CapacityWrites == writes && SquadPrivacy.Mode == SquadPrivacyMode.Private, "Non-leaders must not change privacy or capacity." );
foreign.Owner.IsMe = true;
SquadPrivacy.Enforce( true );
Check( foreign.MaxMembers == 2 && SquadPrivacy.Limit( foreign ) == 5, "Taking leadership must preserve this squad's original limit." );
SquadPrivacy.Set( SquadPrivacyMode.Open );
Check( foreign.MaxMembers == 5, "Opening a squad after becoming leader must restore its own capacity." );

PartyRoom.Current = null;
SquadPrivacy.Enforce( true );
Check( SquadPrivacy.Limit( null ) == SquadPrivacy.SquadLimit, "No squad must use the normal default capacity." );

SquadPrivacy.Set( SquadPrivacyMode.Private );
var created = await SquadPrivacy.CreateParty();
Check( !created.Listed && created.MaxMembers == 1 && SquadPrivacy.Limit( created ) == SquadPrivacy.SquadLimit,
	"A newly created private squad must be unlisted and retain its normal original capacity." );

// Repeated switching verifies that the cache follows the current room rather than accumulating old limits.
foreach ( var capacity in new[] { 4, 6, 8, 10, 12 } )
{
	var room = Party( 2, capacity );
	PartyRoom.Current = room;
	SquadPrivacy.Enforce( true );
	Check( SquadPrivacy.Limit( room ) == capacity && room.MaxMembers == 2, "Each newly observed private room must retain its own capacity." );
	SquadPrivacy.Set( SquadPrivacyMode.InviteOnly );
	Check( room.MaxMembers == capacity, "Each reopened room must recover its own original capacity." );
	SquadPrivacy.Set( SquadPrivacyMode.Private );
}

Console.WriteLine( $"PASS: {checks} squad privacy checks against production SquadPrivacy." );

// In-memory Steam party and profile stand-ins only. No real squad, invitation, or account is touched.
namespace Sandbox
{
	public readonly record struct RealTimeSince( float Value )
	{
		public static implicit operator RealTimeSince( float value ) => new( value );
		public static bool operator <( RealTimeSince value, float other ) => value.Value < other;
		public static bool operator >( RealTimeSince value, float other ) => value.Value > other;
	}
	public class PartyMember { public bool IsMe { get; set; } }
	public class PartyRoom
	{
		public static PartyRoom Current { get; set; }
		public PartyMember Owner { get; set; } = new() { IsMe = true };
		public int MemberCount { get; set; } = 1;
		public bool Listed { get; set; }
		private int _capacity;
		public int CapacityWrites;
		public int MaxMembers { get => _capacity; set { _capacity = value; CapacityWrites++; } }
		public static Task<PartyRoom> Create( int limit, string name, bool listed )
		{
			Current = new PartyRoom { MaxMembers = limit, Listed = listed };
			return Task.FromResult( Current );
		}
		public void Leave() { if ( Current == this ) Current = null; }
	}
	public static class Game { public static Cookies Cookies { get; } = new(); }
	public class Cookies
	{
		private readonly Dictionary<string, object> _values = new();
		public T Get<T>( string key, T fallback ) => _values.TryGetValue( key, out var value ) ? (T)value : fallback;
		public void Set<T>( string key, T value ) => _values[key] = value;
	}
}
