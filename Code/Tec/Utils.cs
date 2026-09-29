using Facepunch;

namespace Tec;

public static class Utils
{
	public static Sandbox.DamageInfo CreateDamageInfo( Facepunch.DamageInfo damageInfo )
	{
		return new Sandbox.DamageInfo( damageInfo.Damage, damageInfo.Attacker?.GameObject, damageInfo.Inflictor?.GameObject )
		{
			Position = damageInfo.Position
		};
	}
	
	public static Facepunch.DamageInfo CreateDamageInfo( Sandbox.DamageInfo damageInfo)
	{
		var tags = damageInfo.Hitbox.GetHitboxTags();

		var force = damageInfo.Damage * (damageInfo.Position - damageInfo.Origin).Normal;
		return new Facepunch.DamageInfo(damageInfo.Attacker.GetComponent<Component>(),damageInfo.Damage, damageInfo.Weapon.GetComponent<Component>(),damageInfo.Position, force, tags);
	}
}
