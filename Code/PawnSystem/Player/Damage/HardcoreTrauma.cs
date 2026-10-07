namespace Facepunch;

public enum TraumaRegion { Head, Chest, Abdomen, Limb }

/// <summary>
/// Game approximation of immediate trauma using the weapon's damage after range/penetration loss.
/// These coefficients are gameplay calibration, not medical probabilities or an organ simulation.
/// No floor: a weak distant pellet cannot become an automatic lethal head hit.
/// </summary>
public static class HardcoreTrauma
{
	public static float Damage( float roundDamage, TraumaRegion region, float maxHealth )
	{
		if ( roundDamage <= 0f || maxHealth <= 0f ) return 0f;
		return region switch
		{
			TraumaRegion.Head => roundDamage * 10f,
			TraumaRegion.Chest => roundDamage * 4.5f,
			TraumaRegion.Abdomen => roundDamage * 3f,
			_ => System.MathF.Min( roundDamage * 1.7f, maxHealth * 0.5f )
		};
	}
}
