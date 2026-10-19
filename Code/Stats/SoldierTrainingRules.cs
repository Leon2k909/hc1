using System;

namespace Facepunch;

public enum SoldierSkill { Endurance, Handling }

/// <summary>Shared, deterministic training curves and stamina rules. No profile or engine state.</summary>
public static class SoldierTrainingRules
{
	public const int MaxLevel = 50;
	public const float MetresPerEnduranceXP = 10f;
	public const float ShotAwardInterval = 2f;
	public const float HitAwardInterval = 0.5f;
	public const float BaseSprintSeconds = 12f;
	public const float BaseRecoverySeconds = 6f;
	public const float RecoveryDelay = 1.25f;
	public const float ExhaustionRecovery = 0.25f;

	public static int XPForLevel( int level )
	{
		var completed = Math.Clamp( level, 1, MaxLevel ) - 1;
		return completed * 100 + completed * (completed - 1) * 20;
	}

	public static int ClampXP( int xp ) => Math.Clamp( xp, 0, XPForLevel( MaxLevel ) );

	public static int AddXP( int xp, int award )
		=> (int)Math.Min( (long)ClampXP( xp ) + Math.Max( 0, award ), XPForLevel( MaxLevel ) );

	public static int LevelForXP( int xp )
	{
		xp = ClampXP( xp );
		var level = 1;
		while ( level < MaxLevel && xp >= XPForLevel( level + 1 ) ) level++;
		return level;
	}

	public static int XPIntoLevel( int xp ) => ClampXP( xp ) - XPForLevel( LevelForXP( xp ) );

	public static int XPToNextLevel( int xp )
	{
		var level = LevelForXP( xp );
		return level == MaxLevel ? 0 : XPForLevel( level + 1 ) - ClampXP( xp );
	}

	public static float LevelProgress( int xp )
	{
		var level = LevelForXP( xp );
		if ( level == MaxLevel ) return 1f;
		return XPIntoLevel( xp ) / (float)(XPForLevel( level + 1 ) - XPForLevel( level ));
	}

	/// <summary>Benefits grow within a level too; the rising XP curve makes later improvements take longer.</summary>
	public static float Mastery( int xp )
		=> Math.Clamp( (LevelForXP( xp ) - 1f + LevelProgress( xp )) / (MaxLevel - 1f), 0f, 1f );

	public static float SprintCapacityScale( int xp ) => 1f + 0.20f * Mastery( xp );
	public static float RecoveryScale( int xp ) => 1f + 0.15f * Mastery( xp );
	public static float RecoilScale( int xp ) => 1f - 0.12f * Mastery( xp );
	public static float SwayScale( int xp ) => 1f - 0.15f * Mastery( xp );
	public static float AimTimeScale( int xp ) => 1f - 0.10f * Mastery( xp );
	public static float ReloadTimeScale( int xp ) => 1f - 0.10f * Mastery( xp );

	/// <summary>Only plausible ground travel counts: no standing against a wall, spawn jumps, teleports or stale samples.</summary>
	public static float RunningMetres( float distance, float elapsed, float velocity, float wishSpeed, bool eligible )
	{
		if ( !eligible || !float.IsFinite( distance ) || !float.IsFinite( elapsed )
			|| !float.IsFinite( velocity ) || !float.IsFinite( wishSpeed )
			|| elapsed < 0.1f || elapsed > 1f || distance <= 0f || velocity < 40f ) return 0f;
		var speed = distance / elapsed;
		if ( speed < 60f || speed > Math.Max( wishSpeed, 60f ) * 1.35f + 24f ) return 0f;
		if ( distance > (velocity + 64f) * elapsed + 8f ) return 0f;
		return distance * 0.0254f;
	}

	public readonly struct SprintState
	{
		public float Stamina { get; }
		public bool Exhausted { get; }
		public float RecoveryWait { get; }

		public SprintState( float stamina, bool exhausted, float recoveryWait )
		{
			Stamina = stamina;
			Exhausted = exhausted;
			RecoveryWait = recoveryWait;
		}
	}

	/// <summary>Normalized stamina keeps the HUD and exhaustion thresholds independent of the trained capacity.</summary>
	public static SprintState StepStamina( SprintState state, bool running, float delta, int enduranceXP )
	{
		var stamina = float.IsFinite( state.Stamina ) ? Math.Clamp( state.Stamina, 0f, 1f ) : 1f;
		var wait = float.IsFinite( state.RecoveryWait ) ? Math.Clamp( state.RecoveryWait, 0f, RecoveryDelay ) : 0f;
		delta = float.IsFinite( delta ) ? Math.Clamp( delta, 0f, 0.25f ) : 0f;
		var exhausted = state.Exhausted;

		if ( running && !exhausted )
		{
			stamina = Math.Max( 0f, stamina - delta / (BaseSprintSeconds * SprintCapacityScale( enduranceXP )) );
			wait = RecoveryDelay;
			if ( stamina <= 0.00001f ) { stamina = 0f; exhausted = true; }
		}
		else
		{
			var recoveryTime = Math.Max( 0f, delta - wait );
			wait = Math.Max( 0f, wait - delta );
			stamina = Math.Min( 1f, stamina + recoveryTime * RecoveryScale( enduranceXP ) / BaseRecoverySeconds );
			if ( stamina >= ExhaustionRecovery ) exhausted = false;
		}

		return new SprintState( stamina, exhausted, wait );
	}
}
