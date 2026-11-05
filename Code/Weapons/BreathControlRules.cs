using System;

namespace Facepunch;

/// <summary>Gameplay breath control: a short steadying window, followed by recovery. No engine state.</summary>
public static class BreathControlRules
{
	public const float HoldSeconds = 4f;
	public const float RecoverySeconds = 8f;
	public const float MinimumStamina = 0.35f;
	public const float SteadySwayScale = 0.3f;

	public readonly record struct State( float Spent, float Weight, bool NeedsRelease );
	public readonly record struct Sample( State State, bool Holding )
	{
		public float SwayScale => 1f - (1f - SteadySwayScale) * State.Weight;
	}

	public static Sample Step( State state, float delta, bool eligible, bool held, float stamina )
	{
		delta = float.IsFinite( delta ) ? Math.Clamp( delta, 0f, 0.25f ) : 0f;
		var spent = float.IsFinite( state.Spent ) ? Math.Clamp( state.Spent, 0f, HoldSeconds ) : HoldSeconds;
		var weight = float.IsFinite( state.Weight ) ? Math.Clamp( state.Weight, 0f, 1f ) : 0f;
		var blocked = state.NeedsRelease || spent >= HoldSeconds - 0.00001f;
		// After a forced stop, recover at least three quarters of the reserve and release the action.
		if ( !held && spent <= HoldSeconds * 0.25f ) blocked = false;
		eligible &= float.IsFinite( stamina ) && stamina >= MinimumStamina;
		if ( held && !eligible ) blocked = true;
		var holding = eligible && held && !blocked;
		if ( holding )
		{
			spent = MathF.Min( HoldSeconds, spent + delta );
			if ( spent >= HoldSeconds - 0.00001f )
			{
				spent = HoldSeconds;
				blocked = true;
				holding = false;
			}
		}
		else
		{
			spent = MathF.Max( 0f, spent - delta * HoldSeconds / RecoverySeconds );
		}
		var target = holding ? 1f : 0f;
		weight = target + (weight - target) * MathF.Exp( -delta * 10f );
		return new( new( spent, weight, blocked ), holding );
	}
}
