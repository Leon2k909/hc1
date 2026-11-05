using System;

namespace Facepunch;

/// <summary>Loaded-round mass, using the existing ROUND_KG / GUN_ROUND data in Tools/part_masses.py.</summary>
public static class LoadedAmmoMassRules
{
	// Unlisted loads deliberately retain their existing behavior instead of guessing cartridge weights.
	public static float CartridgeKg( string weaponPath ) => weaponPath?.Replace( '\\', '/' ).ToLowerInvariant() switch
	{
		"weapons/m4a1/m4a1.equip" or "weapons/m16/m16.equip" or "weapons/m16a2/m16a2.equip"
			or "weapons/aug/aug.equip" or "weapons/famas/famas.equip" or "weapons/mcx/mcx.equip"
			or "weapons/hk416/hk416.equip" => 0.0123f,
		"weapons/kastov74u/kastov74u.equip" or "weapons/ak105/ak105.equip" or "weapons/ak12/ak12.equip"
			or "weapons/ak74m/ak74m.equip" or "weapons/rpk16/rpk16.equip" => 0.0105f,
		"weapons/kastov/kastov762.equip" or "weapons/rpk/rpk.equip" or "weapons/ak15/ak15.equip" => 0.0163f,
		"weapons/scarh/scarh.equip" or "weapons/fal/fal.equip" => 0.0254f,
		"weapons/spear/spear.equip" => 0.0194f,
		"weapons/mp5/mp5.equip" or "weapons/vityaz/vityaz.equip" or "weapons/uzi/uzi.equip" => 0.012f,
		"weapons/m18/m18.equip" => 0.0115f,
		"weapons/vepr12/vepr12.equip" => 0.040f,
		_ => 0f
	};

	/// <summary>
	/// Relative recoil velocity versus the same gun with a full magazine. Its full mass already includes fitted
	/// parts and a full fitted magazine. Count rounds immediately before discharge, including any chambered round.
	/// </summary>
	public static float RecoilScale( float fullMassKg, float cartridgeKg, int capacity, long roundsBeforeShot, bool hasChamber )
	{
		if ( !float.IsFinite( fullMassKg ) || fullMassKg <= 0f || !float.IsFinite( cartridgeKg ) || cartridgeKg <= 0f
			|| capacity <= 0 || capacity > 1000 ) return 1f;
		var rounds = Math.Clamp( roundsBeforeShot, 0L, (long)capacity + (hasChamber ? 1 : 0) );
		var currentMass = MathF.Max( fullMassKg * 0.5f, fullMassKg + (rounds - capacity) * cartridgeKg );
		return fullMassKg / currentMass;
	}
}
