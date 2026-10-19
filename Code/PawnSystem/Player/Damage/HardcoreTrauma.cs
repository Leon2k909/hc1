namespace Facepunch;

public enum TraumaRegion { Head, Chest, Abdomen, Limb }

/// <summary>
/// Game approximation of immediate trauma using the weapon's damage after range/penetration loss.
/// These coefficients are gameplay calibration, not medical probabilities or an organ simulation.
/// No floor: a weak distant pellet cannot become an automatic lethal head hit.
/// </summary>
public static class HardcoreTrauma
{
	/// <summary>
	/// The chance a body hit kills outright (the heart, a major vessel or the spine) is the round's damage over this, the
	/// way the user asked for it as real life: an M4's (20) roughly two thirds of the time, a 9 mm pistol's or SMG's
	/// (12) 40%, a 7.62x39 AK's (26) 87%, a SCAR-H's (36) and heavier rounds up to <see cref="MaxBodyKillChance"/>.
	/// </summary>
	public const float BodyKillDamage = 30f;
	public const float MaxBodyKillChance = 0.95f;

	/// <summary>A gut or pelvis hit is less often instantly fatal than one to the chest.</summary>
	public const float AbdomenKillScale = 0.6f;

	/// <summary>
	/// A body hit that doesn't kill outright leaves at least this share of health: badly hurt, not dead. So whether one body
	/// hit kills is <see cref="KillChance"/>'s alone, for the heavy rounds too, whose 4.5x chest trauma used to kill every
	/// time.
	/// </summary>
	public const float SurvivedBodyHitHealth = 0.1f;

	public static float Damage( float roundDamage, TraumaRegion region, float maxHealth )
	{
		if ( roundDamage <= 0f || maxHealth <= 0f ) return 0f;
		var survivable = maxHealth * (1f - SurvivedBodyHitHealth);
		return region switch
		{
			TraumaRegion.Head => roundDamage * 10f,
			// Pistol/SMG rounds shouldn't remove almost all health on every surviving hit.
			// A heavier rifle round transfers more trauma, while the fatal-hit roll still
			// lets an occasional victim survive even a powerful chest impact.
			TraumaRegion.Chest => System.MathF.Min( roundDamage *
				(3f + 1.5f * System.Math.Clamp( (roundDamage - 12f) / 8f, 0f, 1f )), survivable ),
			TraumaRegion.Abdomen => System.MathF.Min( roundDamage * 3f, survivable ),
			_ => System.MathF.Min( roundDamage * 1.7f, maxHealth * 0.5f )
		};
	}

	/// <summary>
	/// The chance a hit to <paramref name="region"/> kills outright, on top of its <see cref="Damage"/>. Only the chest
	/// and abdomen roll: a head hit's damage kills by itself, a limb's never does. More health than
	/// <paramref name="referenceHealth"/> (a custom game's) makes it rarer, less makes it likelier, and armour lowers it by
	/// the share of the hit it stops (<paramref name="transmission"/>: 1 unprotected, 0 stopped).
	/// </summary>
	public static float KillChance( float roundDamage, TraumaRegion region, float maxHealth, float transmission, float referenceHealth = 100f )
	{
		if ( roundDamage <= 0f || maxHealth <= 0f || region is TraumaRegion.Head or TraumaRegion.Limb ) return 0f;
		var chance = System.MathF.Min( roundDamage / BodyKillDamage * (referenceHealth / maxHealth), MaxBodyKillChance );
		if ( region == TraumaRegion.Abdomen ) chance *= AbdomenKillScale;
		return chance * System.Math.Clamp( transmission, 0f, 1f );
	}
}
