namespace Facepunch;

/// <summary>
/// The local soldier profile, using the same cookie storage as player/weapon ranks. Account-scoped and versioned;
/// training survives deaths, map changes and prestige. The host sends earned progress; the owner saves it.
/// </summary>
public static class SoldierTraining
{
	private static ulong _account;
	private static bool _loaded;
	private static bool _dirty;
	private static int _enduranceXP;
	private static int _handlingXP;
	private static RealTimeSince _timeSinceSave;
	public static int Revision { get; private set; }
	public static int LevelUpRevision { get; private set; }
	public static SoldierSkill LastImprovedSkill { get; private set; }
	public static RealTimeSince TimeSinceLevelUp { get; private set; } = 999f;

	private static string Key( SoldierSkill skill ) => $"hc1.training.v1.{_account}.{skill}";

	private static void EnsureLoaded()
	{
		if ( _loaded && _account == Game.SteamId ) return;
		// Finish the previous account's pending save before changing the key namespace.
		Flush();
		_account = Game.SteamId;
		_enduranceXP = SoldierTrainingRules.ClampXP( Game.Cookies.Get( Key( SoldierSkill.Endurance ), 0 ) );
		_handlingXP = SoldierTrainingRules.ClampXP( Game.Cookies.Get( Key( SoldierSkill.Handling ), 0 ) );
		_loaded = true;
		_dirty = false;
		TimeSinceLevelUp = 999f;
		Revision++;
	}

	public static int GetXP( SoldierSkill skill )
	{
		EnsureLoaded();
		return skill == SoldierSkill.Endurance ? _enduranceXP : _handlingXP;
	}

	public static int GetLevel( SoldierSkill skill ) => SoldierTrainingRules.LevelForXP( GetXP( skill ) );

	internal static void Receive( int enduranceXP, int handlingXP, bool announce )
	{
		EnsureLoaded();
		// A delayed snapshot or a reconnect must never undo permanent training already saved on this account.
		enduranceXP = Math.Max( _enduranceXP, SoldierTrainingRules.ClampXP( enduranceXP ) );
		handlingXP = Math.Max( _handlingXP, SoldierTrainingRules.ClampXP( handlingXP ) );
		if ( enduranceXP == _enduranceXP && handlingXP == _handlingXP ) return;

		var enduranceLevelUp = SoldierTrainingRules.LevelForXP( enduranceXP ) > SoldierTrainingRules.LevelForXP( _enduranceXP );
		var handlingLevelUp = SoldierTrainingRules.LevelForXP( handlingXP ) > SoldierTrainingRules.LevelForXP( _handlingXP );
		_enduranceXP = enduranceXP;
		_handlingXP = handlingXP;
		_dirty = true;
		Revision++;
		if ( announce && (enduranceLevelUp || handlingLevelUp) )
		{
			LastImprovedSkill = handlingLevelUp ? SoldierSkill.Handling : SoldierSkill.Endurance;
			TimeSinceLevelUp = 0f;
			LevelUpRevision++;
			Flush();
		}
	}

	internal static void FlushIfDue()
	{
		if ( _dirty && _timeSinceSave >= 5f ) Flush();
	}

	internal static void Flush()
	{
		if ( !_loaded || !_dirty ) return;
		Game.Cookies.Set( Key( SoldierSkill.Endurance ), _enduranceXP );
		Game.Cookies.Set( Key( SoldierSkill.Handling ), _handlingXP );
		_dirty = false;
		_timeSinceSave = 0f;
	}
}
