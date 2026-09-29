namespace Facepunch;

public enum ChallengeKind
{
	Kills,
	Headshots,
	Wins,
	Matches,
}

/// <summary>
/// Three challenges a day, the same three for everyone, swapped at midnight UTC.
/// Progress lives in cookies like <see cref="Progression"/>, and a challenge pays its XP the moment it's done.
/// </summary>
public static class DailyChallenges
{
	public record Definition( ChallengeKind Kind, int Goal, int Xp )
	{
		/// <summary>What to do, in the player's language. Only read where it's shown (the hub's sidebar).</summary>
		public string Title => Kind switch
		{
			ChallengeKind.Kills => Tr( "Get {0} Operator Kills", Goal ),
			ChallengeKind.Headshots => Tr( "Get {0} Headshots", Goal ),
			ChallengeKind.Wins => Goal == 1 ? Tr( "Win a Match" ) : Tr( "Win {0} Matches", Goal ),
			_ => Goal == 1 ? Tr( "Finish a Match" ) : Tr( "Finish {0} Matches", Goal ),
		};

		public string Icon => Kind switch
		{
			ChallengeKind.Kills => "gps_fixed",
			ChallengeKind.Headshots => "crisis_alert",
			ChallengeKind.Wins => "emoji_events",
			_ => "sports_esports",
		};
	}

	public readonly record struct Challenge( Definition Definition, int Progress )
	{
		public bool IsComplete => Progress >= Definition.Goal;
		public float Fraction => Math.Clamp( Progress / (float)Definition.Goal, 0f, 1f );
	}

	/// <summary>Each kind's difficulties. A day uses three of the four kinds, one difficulty each.</summary>
	private static readonly Definition[][] Pool =
	{
		new Definition[] { new( ChallengeKind.Kills, 15, 1500 ), new( ChallengeKind.Kills, 25, 2500 ), new( ChallengeKind.Kills, 40, 3500 ) },
		new Definition[] { new( ChallengeKind.Headshots, 5, 2500 ), new( ChallengeKind.Headshots, 10, 3500 ) },
		new Definition[] { new( ChallengeKind.Wins, 1, 1500 ), new( ChallengeKind.Wins, 3, 2500 ) },
		new Definition[] { new( ChallengeKind.Matches, 3, 1500 ), new( ChallengeKind.Matches, 5, 2500 ) },
	};

	private const int SlotCount = 3;
	private const string DayCookie = "hc1.daily.day";
	private static string ProgressCookie( int slot ) => $"hc1.daily.progress.{slot}";

	/// <summary>Whole days since year 1 (UTC). A new set starts when it ticks over.</summary>
	public static int Today => (int)(DateTime.UtcNow.Ticks / TimeSpan.TicksPerDay);

	public static TimeSpan TimeUntilReset => TimeSpan.FromTicks( TimeSpan.TicksPerDay - DateTime.UtcNow.Ticks % TimeSpan.TicksPerDay );

	/// <summary>Goes up whenever progress changes, for UI build hashes.</summary>
	public static int Version { get; private set; }

	private static int _cachedDay = -1;
	private static Definition[] _cachedSet;

	/// <summary>A day's three challenges, always in the same kind order.</summary>
	public static Definition[] ForDay( int day )
	{
		if ( day == _cachedDay ) return _cachedSet;

		var resting = Pick( day, 0, Pool.Length );
		var set = new List<Definition>();
		for ( var kind = 0; kind < Pool.Length; kind++ )
		{
			if ( kind == resting ) continue;
			set.Add( Pool[kind][Pick( day, kind + 1, Pool[kind].Length )] );
		}

		_cachedDay = day;
		_cachedSet = set.ToArray();
		return _cachedSet;
	}

	/// <summary>Today's challenges with the local player's progress.</summary>
	public static IEnumerable<Challenge> Current
	{
		get
		{
			ResetIfNewDay();
			var set = ForDay( Today );
			for ( var i = 0; i < set.Length; i++ )
				yield return new Challenge( set[i], GetProgress( i ) );
		}
	}

	/// <summary>The local player killed an operator. Runs on the killer's own machine.</summary>
	public static void OnKill( bool headshot )
	{
		Add( ChallengeKind.Kills );
		if ( headshot ) Add( ChallengeKind.Headshots );
	}

	/// <summary>A match the local player was in has ended.</summary>
	public static void OnMatchFinished( bool won )
	{
		Add( ChallengeKind.Matches );
		if ( won ) Add( ChallengeKind.Wins );
	}

	private static void Add( ChallengeKind kind )
	{
		ResetIfNewDay();
		var set = ForDay( Today );
		for ( var i = 0; i < set.Length; i++ )
		{
			var challenge = set[i];
			var progress = GetProgress( i );
			if ( challenge.Kind != kind || progress >= challenge.Goal ) continue;

			Game.Cookies.Set( ProgressCookie( i ), progress + 1 );
			Version++;

			// Paid once, on the step that finishes it.
			if ( progress + 1 >= challenge.Goal )
				Progression.AddXP( challenge.Xp );
		}
	}

	private static int GetProgress( int slot ) => Math.Max( 0, Game.Cookies.Get( ProgressCookie( slot ), 0 ) );

	private static void ResetIfNewDay()
	{
		var today = Today;
		if ( Game.Cookies.Get( DayCookie, 0 ) == today ) return;

		Game.Cookies.Set( DayCookie, today );
		for ( var i = 0; i < SlotCount; i++ )
			Game.Cookies.Set( ProgressCookie( i ), 0 );
		Version++;
	}

	/// <summary>A stable pseudo-random index for a day, so everyone lands on the same set.</summary>
	private static int Pick( int day, int salt, int count )
	{
		unchecked
		{
			var h = (uint)day * 2654435761u + (uint)salt * 40503u;
			h ^= h >> 16;
			h *= 2246822519u;
			h ^= h >> 13;
			return (int)(h % (uint)count);
		}
	}
}
