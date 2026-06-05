namespace Facepunch;

/// <summary>
/// Cookie-based persistent player progression: level 1–100, XP that scales like CoD.
/// </summary>
public static class Progression
{
	public const int MaxLevel = 55;
	private const string XpCookie = "hc1.progress.xp";
	private const string PrestigeCookie = "hc1.progress.prestige";
	public static int GetPrestige()
	{
		if ( Game.SteamId == 76561198271608270ul ) return 10;
		return Game.Cookies.Get( PrestigeCookie, 0 );
	}

	public static void EnterPrestigeMode()
	{
		var level = GetLevel();
		if ( level < MaxLevel ) return;

		var prestige = GetPrestige();
		if ( prestige >= 10 ) return; // Max prestige 10

		Game.Cookies.Set( PrestigeCookie, prestige + 1 );
		Game.Cookies.Set( XpCookie, 0 );

		// Reset all weapon XP (attachment unlocks reset)
		var weapons = ResourceLibrary.GetAll<EquipmentResource>();
		foreach ( var wep in weapons )
		{
			Game.Cookies.Set( $"hc1.weapon.xp.{wep.ResourceName}", 0 );
		}
	}

	/// <summary>Total accumulated XP stored in a cookie.</summary>
	public static int GetXP() => Math.Max( 0, Game.Cookies.Get( XpCookie, 0 ) );

	/// <summary>Current player level (1–100) derived from stored XP.</summary>
	public static int GetLevel() => GetLevelForXP( GetXP() );

	/// <summary>XP earned within the current level.</summary>
	public static int GetXPIntoLevel()
	{
		return GetXP() - GetXPForLevel( GetLevel() );
	}

	/// <summary>XP needed to complete the current level (reach next).</summary>
	public static int GetXPForNextLevel()
	{
		var level = GetLevel();
		if ( level >= MaxLevel ) return 0;
		return GetXPForLevel( level + 1 ) - GetXPForLevel( level );
	}

	/// <summary>0–1 progress through the current level.</summary>
	public static float GetLevelProgress()
	{
		var required = GetXPForNextLevel();
		if ( required <= 0 ) return 1f;
		return Math.Clamp( GetXPIntoLevel() / (float)required, 0f, 1f );
	}

	/// <summary>Total XP required to reach the start of <paramref name="level"/>.</summary>
	public static int GetXPForLevel( int level )
	{
		var completed = Math.Clamp( level, 1, MaxLevel ) - 1;
		return completed * 500 + completed * (completed - 1) * 75;
	}

	/// <summary>Resolve a level from raw total XP.</summary>
	public static int GetLevelForXP( int xp )
	{
		var level = 1;
		while ( level < MaxLevel && xp >= GetXPForLevel( level + 1 ) )
			level++;
		return level;
	}

	/// <summary>Persist XP gained by the local player (e.g. on kill).</summary>
	public static void AddXP( int amount )
	{
		if ( amount <= 0 ) return;
		var next = Math.Min( GetXP() + amount, GetXPForLevel( MaxLevel ) );
		Game.Cookies.Set( XpCookie, next );
	}
}
