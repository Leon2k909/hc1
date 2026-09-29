using System.Text.Json;

namespace Facepunch;

/// <summary>Visible ranks and placement matches. Matchmaking uses the earned tier, or the placement pool.</summary>
public static class Rank
{
	// A new profile version starts the old automatic Bronze profiles in placements.
	private const string StateCookie = "razed.rank.placements.v1";
	public const int PlacementMatches = 5;
	public const int DivisionsPerTier = 3;
	public const int UnitsPerDivision = 1000;
	public const int UnitsPerTier = UnitsPerDivision * DivisionsPerTier;
	public const int WinProgress = 125;
	public const int LossProgress = 100;
	public const int MaxPlacementUnits = 11 * UnitsPerDivision;
	public const string UnrankedColor = "#aebbc8";

	public static readonly string[] TierNames = { "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master" };
	public static readonly string[] TierColors = { "#cd7f32", "#c4cdd4", "#ffcf40", "#4fd0e0", "#8a6cff", "#ff5c5c" };
	private static readonly string[] DivisionNumerals = { "III", "II", "I" };
	public static int MaxTierIndex => TierNames.Length - 1;

	/// <summary>Saved together so a result and its duplicate guard cannot get out of step.</summary>
	public sealed record RankState
	{
		public int Season { get; init; }
		public int Placements { get; init; }
		public float PlacementScore { get; init; }
		public int ProgressUnits { get; init; }
		public int SeasonHighUnits { get; init; }
		public string LastMatchId { get; init; } = "";
		public bool IsPlaced => Placements >= PlacementMatches;
	}

	private static string _cachedJson;
	private static RankState _cachedState;
	public static RankState State
	{
		get
		{
			var json = Game.Cookies.Get<string>( StateCookie, "" );
			if ( _cachedState is not null && json == _cachedJson ) return _cachedState;
			_cachedJson = json;
			try { _cachedState = string.IsNullOrEmpty( json ) ? new() : JsonSerializer.Deserialize<RankState>( json ) ?? new(); }
			catch ( JsonException ) { _cachedState = new(); }
			return _cachedState;
		}
	}

	private static void Save( RankState state )
	{
		_cachedState = state;
		_cachedJson = JsonSerializer.Serialize( state );
		Game.Cookies.Set( StateCookie, _cachedJson );
	}

	public static bool IsPlaced => State.Season == GetSeason() && State.IsPlaced;
	public static int PlacementsCompleted => State.Season == GetSeason() ? Math.Clamp( State.Placements, 0, PlacementMatches ) : 0;
	public static int PlacementsRemaining => PlacementMatches - PlacementsCompleted;
	public static int GetProgressUnits() => IsPlaced ? State.ProgressUnits : 0;
	public static int GetTierIndex() => IsPlaced ? GetTierIndex( State.ProgressUnits ) : -1;
	public static int GetTierIndex( int units ) => Math.Clamp( units / UnitsPerTier, 0, MaxTierIndex );
	public static string GetTierName() => IsPlaced ? TierNames[GetTierIndex()] : "Unranked";
	public static string GetTierColor() => IsPlaced ? TierColors[GetTierIndex()] : UnrankedColor;
	public static string GetEmblem( int tier ) => $"/ui/ranked/{(tier < 0 ? "unranked" : TierNames[Math.Clamp( tier, 0, MaxTierIndex )].ToLowerInvariant())}.png";
	public static string GetRankName() => IsPlaced ? GetRankName( State.ProgressUnits ) : "Unranked";
	public static string GetRankName( int units )
	{
		var tier = GetTierIndex( units );
		return tier == MaxTierIndex ? TierNames[tier] : $"{TierNames[tier]} {DivisionNumerals[Math.Max( 0, units ) % UnitsPerTier / UnitsPerDivision]}";
	}

	public static float GetDivisionProgress() => !IsPlaced ? 0f : GetTierIndex() == MaxTierIndex ? 1f : (State.ProgressUnits % UnitsPerDivision) / (float)UnitsPerDivision;
	public static float GetTierProgress() => !IsPlaced ? 0f : GetTierIndex() == MaxTierIndex ? 1f : (State.ProgressUnits % UnitsPerTier) / (float)UnitsPerTier;
	public static string GetNextRankName() => !IsPlaced || GetTierIndex() == MaxTierIndex ? null : GetRankName( (State.ProgressUnits / UnitsPerDivision + 1) * UnitsPerDivision );
	public static int GetNextTierIndex() => !IsPlaced ? -1 : GetTierIndex( Math.Min( (State.ProgressUnits / UnitsPerDivision + 1) * UnitsPerDivision, MaxTierIndex * UnitsPerTier ) );
	public static int GetSeasonHighTier() => IsPlaced ? GetTierIndex( State.SeasonHighUnits ) : -1;
	public static string GetSeasonHighName() => IsPlaced ? GetRankName( State.SeasonHighUnits ) : "Unranked";
	public static string MatchTag() => $"[R:{GetTierName().ToUpperInvariant()}]";

	/// <summary>
	/// A rank or tier name from here ("Gold III", "Unranked") in the player's language, for showing only: the English
	/// is what's saved and what lobbies are tagged with. The tier is translated and the division numeral kept, which is
	/// the order in every language. Pass it in capitals ("GOLD III") to get it back in capitals.
	/// </summary>
	public static string Translate( string rankName )
	{
		if ( string.IsNullOrEmpty( rankName ) ) return rankName;
		var space = rankName.LastIndexOf( ' ' );
		var numeral = space > 0 ? rankName.Substring( space + 1 ) : null;
		return numeral is not null && DivisionNumerals.Contains( numeral )
			? $"{Tr( rankName.Substring( 0, space ) )} {numeral}"
			: Tr( rankName );
	}

	/// <summary>
	/// Placements weigh the match result 70% and score contribution 30%. Performance is 0..1, with 0.5 an average
	/// contribution. Five games place from Bronze III to Platinum I; the remaining ladder is earned in ranked play.
	/// Draws count as completed placements and half a win. After placement, a draw leaves progress unchanged.
	/// </summary>
	public static RankState ApplyResult( RankState state, string matchId, bool won, bool draw, float performance, int season )
	{
		if ( string.IsNullOrWhiteSpace( matchId ) || matchId == state.LastMatchId ) return state;
		state = ForSeason( state, season );
		if ( !state.IsPlaced )
		{
			var result = draw ? 0.5f : won ? 1f : 0f;
			performance = float.IsFinite( performance ) ? Math.Clamp( performance, 0f, 1f ) : 0.5f;
			var completed = Math.Clamp( state.Placements + 1, 1, PlacementMatches );
			var score = state.PlacementScore + result * 0.7f + performance * 0.3f;
			var units = completed == PlacementMatches ? (int)MathF.Round( score / PlacementMatches * MaxPlacementUnits ) : 0;
			return state with { Placements = completed, PlacementScore = score, ProgressUnits = units, SeasonHighUnits = units, LastMatchId = matchId };
		}

		var progress = Math.Clamp( state.ProgressUnits + (draw ? 0 : won ? WinProgress : -LossProgress), 0, MaxTierIndex * UnitsPerTier );
		return state with { ProgressUnits = progress, SeasonHighUnits = Math.Max( state.SeasonHighUnits, progress ), LastMatchId = matchId };
	}

	public static void RecordResult( string matchId, bool won, bool draw, float performance )
		=> Save( ApplyResult( State, matchId, won, draw, performance, GetSeason() ) );

	public const int MonthsPerSeason = 3;
	private static DateTime SeasonOneStart => new( 2026, 9, 1, 0, 0, 0, DateTimeKind.Utc );
	public static int GetSeason() => GetSeason( DateTime.UtcNow );
	public static int GetSeason( DateTime utc ) => Math.Max( 1, ((utc.Year - SeasonOneStart.Year) * 12 + utc.Month - SeasonOneStart.Month) / MonthsPerSeason + 1 );
	public static DateTime GetSeasonEnd( int season ) => SeasonOneStart.AddMonths( season * MonthsPerSeason );
	public static TimeSpan GetSeasonTimeLeft() => GetSeasonEnd( GetSeason() ) - DateTime.UtcNow;
	public static RankState ForSeason( RankState state, int season ) => state.Season == season ? state : new() { Season = season, LastMatchId = state.LastMatchId };
	public static void CheckSeason()
	{
		if ( State.Season != GetSeason() ) Save( ForSeason( State, GetSeason() ) );
	}
}
