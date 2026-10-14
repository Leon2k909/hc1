using System;

namespace Facepunch;

public enum LpgCanisterPhase { Intact, Leaking, Burning, Empty, Ruptured }

/// <summary>
/// Game-scaled fuel loss and thermal exposure. A puncture releases fuel; ignition is a separate event.
/// More holes empty the bottle faster. Only sustained heating of a bottle with fuel can rupture it.
/// </summary>
public sealed class LpgCanisterState
{
	public const float SingleHoleDrainTime = 90f;
	public const float ReliefHeat = 12f;
	public const float RuptureHeat = 30f;

	public LpgCanisterPhase Phase { get; private set; }
	public float Fuel { get; private set; } = 1f;
	public float Heat { get; private set; }
	public int Holes { get; private set; }
	public float Pressure => MathF.Sqrt( Fuel );
	public bool HasFuel => Fuel > 0f && Phase is not LpgCanisterPhase.Ruptured;
	public bool IsReleasing => Phase is LpgCanisterPhase.Leaking or LpgCanisterPhase.Burning;

	public void Puncture( int holes = 1 )
	{
		if ( !HasFuel || holes <= 0 ) return;
		Holes = Math.Min( Holes + holes, 12 );
		if ( Phase == LpgCanisterPhase.Intact ) Phase = LpgCanisterPhase.Leaking;
	}

	public void Ignite()
	{
		if ( Phase == LpgCanisterPhase.Leaking && HasFuel ) Phase = LpgCanisterPhase.Burning;
	}

	public void Step( float seconds, float externalHeat, bool ignition )
	{
		if ( !float.IsFinite( seconds ) || seconds <= 0f || !HasFuel ) return;
		externalHeat = float.IsFinite( externalHeat ) ? Math.Clamp( externalHeat, 0f, 3f ) : 0f;
		var heating = externalHeat + (Phase == LpgCanisterPhase.Burning ? 0.8f * Pressure : 0f);
		Heat = Math.Max( 0f, Heat + seconds * (heating > 0.05f ? heating : -0.3f) );

		// The relief valve vents before the vessel fails. Flames can then catch the escaping gas.
		if ( Phase == LpgCanisterPhase.Intact && Heat >= ReliefHeat ) Puncture();
		if ( ignition ) Ignite();

		if ( IsReleasing )
		{
			Fuel = Math.Max( 0f, Fuel - seconds * Holes / SingleHoleDrainTime * (0.3f + 0.7f * Pressure) );
			if ( Fuel <= 0f ) { Phase = LpgCanisterPhase.Empty; return; }
		}

		if ( Heat >= RuptureHeat && Fuel > 0.05f ) Phase = LpgCanisterPhase.Ruptured;
	}

	public void Restore( LpgCanisterPhase phase, float fuel, float heat, int holes )
	{
		Phase = phase;
		Fuel = Math.Clamp( fuel, 0f, 1f );
		Heat = Math.Max( heat, 0f );
		Holes = Math.Clamp( holes, 0, 12 );
	}

	public void Reset() => Restore( LpgCanisterPhase.Intact, 1f, 0f, 0 );
}
