global using Sandbox;
using Facepunch;
using System.Reflection;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
var cached = typeof( RecentFriends ).GetField( "_entries", BindingFlags.Static | BindingFlags.NonPublic );
RecentFriends.Entry[] Load( string saved )
{
	Game.Cookies.Set( "hc1.friends.recent", saved );
	cached.SetValue( null, null ); // Simulate loading a saved profile, without touching real game cookies.
	return RecentFriends.All.ToArray();
}

var loaded = Load( "1:20;2:30;1:10;2:40;3:50" );
Check( loaded.Select( entry => entry.SteamId ).SequenceEqual( new ulong[] { 3, 2, 1 } ), "Repeated saved friends must appear once, newest first." );
Check( loaded.Single( entry => entry.SteamId == 2 ).LastSeen == 40, "Deduplication must retain each friend's newest encounter." );

loaded = Load( "invalid;0:10;7:-1;bad:12;123:bad;45:4:5;9:25;10:0" );
Check( loaded.Select( entry => entry.SteamId ).SequenceEqual( new ulong[] { 9, 10 } ), "Invalid IDs, negative timestamps and malformed records must be skipped without hiding valid friends." );

loaded = Load( string.Join( ';', Enumerable.Range( 1, 35 ).Select( value => $"{value}:{value}" ) ) );
Check( loaded.Length == 20 && loaded[0].SteamId == 35 && loaded[^1].SteamId == 16,
	"Oversized saved histories must keep the newest twenty friends." );

var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
loaded = Load( $"1:{now + 100000};2:{now - 100}" );
Check( loaded[0].LastSeen <= DateTimeOffset.UtcNow.ToUnixTimeSeconds(), "Future timestamps must not pin encounters years ahead of real time." );

Load( "1:10;1:20;2:30" );
RecentFriends.Remember( 3 );
var saved = Game.Cookies.Get( "hc1.friends.recent", "" );
Check( RecentFriends.All.Count() == 3 && saved.Split( ';' ).Length == 3, "The next normal save must persist cleaned history without duplicates." );
Check( RecentFriends.Contains( 1 ) && RecentFriends.Contains( 3 ) && !RecentFriends.Contains( 99 ), "Membership lookup must remain correct." );
RecentFriends.Forget( 1 );
Check( !RecentFriends.Contains( 1 ) && RecentFriends.All.Count() == 2, "Forgetting a cleaned friend must remove them fully." );
var version = RecentFriends.Version;
RecentFriends.Remember( 0 );
Check( RecentFriends.Version == version && !RecentFriends.Contains( 0 ), "Invalid new friend IDs must not modify history." );
RecentFriends.Clear();
Check( !RecentFriends.All.Any() && Game.Cookies.Get( "hc1.friends.recent", "nonempty" ) == "", "Clearing history must still persist an empty list." );

foreach ( var empty in new[] { "", ";;;", "not-a-record" } )
	Check( Load( empty ).Length == 0, "Empty or wholly invalid profiles must load an empty list safely." );

Console.WriteLine( $"PASS: {checks} recent-friends checks against production RecentFriends." );

// Profile and Steam services are in-memory stand-ins; production code parses and manages the history.
namespace Sandbox
{
	public readonly record struct RealTimeSince( float Value )
	{
		public static implicit operator RealTimeSince( float value ) => new( value );
		public static bool operator <( RealTimeSince time, float value ) => time.Value < value;
		public static bool operator >( RealTimeSince time, float value ) => time.Value > value;
	}
	public static class Game { public static Cookies Cookies { get; } = new(); }
	public class Cookies
	{
		private readonly Dictionary<string, object> _values = new();
		public T Get<T>( string key, T fallback ) => _values.TryGetValue( key, out var value ) ? (T)value : fallback;
		public void Set<T>( string key, T value ) => _values[key] = value;
	}
	public class Connection
	{
		public static List<Connection> All { get; } = new();
		public static Connection Local => null;
		public ulong SteamId;
	}
	public class Friend( ulong id ) { public ulong Id => id; public bool IsFriend => false; }
	public class PartyMember { public bool IsMe, IsFriend; public ulong Id; }
	public class PartyRoom { public static PartyRoom Current => null; public List<PartyMember> Members { get; } = new(); }
	public class Scene;
	public abstract class GameObjectSystem<T>( Scene scene )
	{
		public Scene Scene => scene;
		protected enum Stage { FinishUpdate }
		protected void Listen( Stage stage, int priority, Action callback, string name ) { }
	}
}
namespace Facepunch { public static class SquadPrivacy { public static void Enforce() { } } }
