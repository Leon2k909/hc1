namespace Facepunch;

/// <summary>
/// Cookie-based per-weapon progression: level 1–30, XP that scales per weapon like CoD weapon levelling.
/// </summary>
public static class WeaponProgression
{
	public const int MaxLevel = 30;

	/// <summary>Total accumulated XP for this weapon.</summary>
	public static int GetXP( EquipmentResource resource )
		=> resource is null ? 0 : Math.Max( 0, Game.Cookies.Get( CookieKey( resource ), 0 ) );

	/// <summary>Lifetime maximum XP for this weapon (persists through prestige).</summary>
	public static int GetLifetimeXP( EquipmentResource resource )
		=> resource is null ? 0 : Math.Max( 0, Game.Cookies.Get( MaxCookieKey( resource ), 0 ) );

	/// <summary>Current weapon level (1–30).</summary>
	public static int GetLevel( EquipmentResource resource )
		=> GetLevelForXP( GetXP( resource ) );

	/// <summary>Lifetime maximum weapon level (1-30) used for camo unlocks.</summary>
	public static int GetLifetimeLevel( EquipmentResource resource )
		=> GetLevelForXP( GetLifetimeXP( resource ) );

	/// <summary>XP earned within the current weapon level.</summary>
	public static int GetXPIntoLevel( EquipmentResource resource )
	{
		return GetXP( resource ) - GetXPForLevel( GetLevel( resource ) );
	}

	/// <summary>XP needed to finish the current weapon level.</summary>
	public static int GetXPForNextLevel( EquipmentResource resource )
	{
		var level = GetLevel( resource );
		if ( level >= MaxLevel ) return 0;
		return GetXPForLevel( level + 1 ) - GetXPForLevel( level );
	}

	/// <summary>0–1 progress through the current weapon level.</summary>
	public static float GetLevelProgress( EquipmentResource resource )
	{
		var required = GetXPForNextLevel( resource );
		if ( required <= 0 ) return 1f;
		return Math.Clamp( GetXPIntoLevel( resource ) / (float)required, 0f, 1f );
	}

	/// <summary>Total XP needed to reach the start of <paramref name="level"/>.</summary>
	public static int GetXPForLevel( int level )
	{
		var completed = Math.Clamp( level, 1, MaxLevel ) - 1;
		return completed * 250 + completed * (completed - 1) * 50;
	}

	/// <summary>Resolve a weapon level from raw total XP.</summary>
	public static int GetLevelForXP( int xp )
	{
		var level = 1;
		while ( level < MaxLevel && xp >= GetXPForLevel( level + 1 ) )
			level++;
		return level;
	}

	/// <summary>Persist XP gained for this weapon (e.g. on kill).</summary>
	public static void AddXP( EquipmentResource resource, int amount )
	{
		if ( amount <= 0 || resource is null ) return;
		var xp = GetXP( resource );
		var next = Math.Min( xp + amount, GetXPForLevel( MaxLevel ) );
		var nextMax = Math.Min( GetLifetimeXP( resource ) + amount, GetXPForLevel( MaxLevel ) );
		
		Game.Cookies.Set( CookieKey( resource ), next );
		Game.Cookies.Set( MaxCookieKey( resource ), nextMax );

		// A new level can unlock a saved part, which the gun then fits (Gunsmith.AttachmentUnlocks).
		if ( GetLevelForXP( next ) != GetLevelForXP( xp ) )
			Gunsmith.GunsmithLoadoutManager.MarkChanged();
	}

	private static string CookieKey( EquipmentResource resource )
		=> $"hc1.weapon.xp.{resource.ResourceName}";

	private static string MaxCookieKey( EquipmentResource resource )
		=> $"hc1.weapon.max_xp.{resource.ResourceName}";
}
