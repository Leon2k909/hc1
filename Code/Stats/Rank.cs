namespace Facepunch;

/// <summary>
/// Visible competitive rank. There is intentionally NO hidden MMR — the rank you
/// can see (your tier) is exactly what matchmaking uses, so you only ever match
/// players in the same tier.
/// </summary>
public static class Rank
{
	private const string SrCookie = "razed.rank.sr";

	/// <summary>SR span of a single tier.</summary>
	public const int SrPerTier = 600;

	public const int WinSr = 25;
	public const int LossSr = 20;

	public static readonly string[] TierNames =
	{
		"Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master"
	};

	/// <summary>Accent colour per tier (hex), used by the ranked UI.</summary>
	public static readonly string[] TierColors =
	{
		"#cd7f32", // Bronze
		"#c4cdd4", // Silver
		"#ffcf40", // Gold
		"#4fd0e0", // Platinum
		"#8a6cff", // Diamond
		"#ff5c5c", // Master
	};

	public static int MaxTierIndex => TierNames.Length - 1;

	/// <summary>Total accumulated SR.</summary>
	public static int GetSR() => System.Math.Max( 0, Game.Cookies.Get( SrCookie, 0 ) );

	/// <summary>Current tier index (0 = Bronze … 5 = Master).</summary>
	public static int GetTierIndex() => System.Math.Clamp( GetSR() / SrPerTier, 0, MaxTierIndex );

	public static string GetTierName() => TierNames[GetTierIndex()];

	public static string GetTierColor() => TierColors[GetTierIndex()];

	/// <summary>SR earned within the current tier.</summary>
	public static int GetSRIntoTier()
		=> GetTierIndex() >= MaxTierIndex ? GetSR() : GetSR() % SrPerTier;

	/// <summary>0..1 progress through the current tier (always 1 at Master).</summary>
	public static float GetTierProgress()
	{
		if ( GetTierIndex() >= MaxTierIndex ) return 1f;
		return System.Math.Clamp( (GetSR() % SrPerTier) / (float)SrPerTier, 0f, 1f );
	}

	public static void AddSR( int amount )
	{
		Game.Cookies.Set( SrCookie, System.Math.Max( 0, GetSR() + amount ) );
	}

	/// <summary>Apply the result of a ranked match.</summary>
	public static void RecordResult( bool won ) => AddSR( won ? WinSr : -LossSr );

	/// <summary>
	/// Matchmaking tag embedded in a ranked lobby's name. Two players only match
	/// when their tags are identical, i.e. they're in the same visible tier.
	/// </summary>
	public static string MatchTag() => MatchTag( GetTierIndex() );

	public static string MatchTag( int tierIndex )
		=> $"[R:{TierNames[System.Math.Clamp( tierIndex, 0, MaxTierIndex )].ToUpperInvariant()}]";
}
