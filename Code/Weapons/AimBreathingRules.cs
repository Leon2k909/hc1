using System;

namespace Facepunch;

/// <summary>Small, continuous aimed breathing. Angles are degrees; no engine or profile state is read here.</summary>
public static class AimBreathingRules
{
	public const float RestBreathsPerMinute = 13f;
	public const float ExertedBreathsPerMinute = 24f;
	private const float AimResponse = 12f;
	private const float FatigueResponse = 2f;

	public readonly struct State
	{
		public double Elapsed { get; }
		public double Phase { get; }
		public float AimWeight { get; }
		public float Fatigue { get; }

		public State( double elapsed, double phase, float aimWeight, float fatigue )
		{
			Elapsed = elapsed;
			Phase = phase;
			AimWeight = aimWeight;
			Fatigue = fatigue;
		}
	}

	public readonly struct Sample
	{
		public State State { get; }
		public float Pitch { get; }
		public float Yaw { get; }

		public Sample( State state, float pitch, float yaw )
		{
			State = state;
			Pitch = pitch;
			Yaw = yaw;
		}
	}

	private static float Unit( float value, float fallback = 0f )
		=> float.IsFinite( value ) ? Math.Clamp( value, 0f, 1f ) : fallback;

	/// <summary>
	/// Stances support the gun without making it perfectly still. Handling keeps its existing 15% cap;
	/// Endurance affects breathing indirectly through the sprint stamina and recovery rules.
	/// </summary>
	public static float SupportScale( bool crouched, bool prone, bool mounted )
		=> mounted ? 0.22f : prone ? 0.42f : crouched ? 0.70f : 1f;

	public static Sample Step( State state, float delta, float aimFraction, float stamina, int handlingXP,
		bool crouched = false, bool prone = false, bool mounted = false )
	{
		delta = float.IsFinite( delta ) ? Math.Clamp( delta, 0f, 0.25f ) : 0f;
		aimFraction = Unit( aimFraction );
		var elapsed = double.IsFinite( state.Elapsed ) ? Math.Max( 0, state.Elapsed ) : 0;
		var phase = double.IsFinite( state.Phase ) ? state.Phase : 0;
		var weight = aimFraction + (Unit( state.AimWeight ) - aimFraction) * MathF.Exp( -delta * AimResponse );
		if ( aimFraction == 0f && weight < 0.0001f ) weight = 0f;

		var previousFatigue = Unit( state.Fatigue );
		var targetFatigue = 1f - Unit( stamina, 1f );
		var decay = Math.Exp( -delta * FatigueResponse );
		var fatigue = targetFatigue + (previousFatigue - targetFatigue) * decay;
		// Integrate the changing breathing rate, rather than resampling time at a new frequency.
		// This keeps the cycle continuous as stamina recovers, independent of rendering rate.
		var fatigueIntegral = targetFatigue * delta + (previousFatigue - targetFatigue) * (1d - decay) / FatigueResponse;
		phase += Math.PI * 2d / 60d * (RestBreathsPerMinute * delta
			+ (ExertedBreathsPerMinute - RestBreathsPerMinute) * fatigueIntegral);
		elapsed += delta;
		var next = new State( elapsed, phase, weight, (float)fatigue );
		var scale = weight * SoldierTrainingRules.SwayScale( handlingXP )
			* SupportScale( crouched, prone, mounted ) * (1f + 0.8f * (float)fatigue);

		// Mostly vertical breathing, slower irregular hand drift, and a very small smooth tremor.
		// Rested novice bounds: 0.119 degrees pitch and 0.0555 yaw, before existing animations/effects.
		var pitch = 0.090d * Math.Sin( phase ) + 0.014d * Math.Sin( phase * 2d + 0.9d )
			+ 0.012d * Math.Sin( elapsed * 0.43d + 1.4d ) + 0.003d * Math.Sin( elapsed * Math.PI * 2d * 5.7d );
		var yaw = 0.039d * Math.Sin( phase + 0.75d ) + 0.014d * Math.Sin( elapsed * 0.67d + 2d )
			+ 0.0025d * Math.Sin( elapsed * Math.PI * 2d * 6.3d + 0.3d );
		return new Sample( next, (float)pitch * scale, (float)yaw * scale );
	}
}
