using Facepunch;

namespace Tec;

public static class Utils
{
	public static Sandbox.DamageInfo CreateDamageInfo( Facepunch.DamageInfo damageInfo )
	{
		// Log.Info($"----------------- CreateDamageInfo {damageInfo.Damage} {damageInfo.Attacker.GameObject} {damageInfo.Inflictor.GameObject}");
		return new Sandbox.DamageInfo(damageInfo.Damage, damageInfo.Attacker.GameObject, damageInfo.Inflictor.GameObject);
	}
	
	public static Facepunch.DamageInfo CreateDamageInfo( Sandbox.DamageInfo damageInfo)
	{
		var tags = HitboxTags.None;

		if ( damageInfo.Hitbox is not null )
		{
			foreach ( var tag in damageInfo.Hitbox.Tags )
			{
				if ( Enum.TryParse<HitboxTags>( tag, true, out var hitboxTag ) )
				{
					tags |= hitboxTag;
				}
			}
		}
		
		var force = damageInfo.Damage * (damageInfo.Position - damageInfo.Origin).Normal;
		return new Facepunch.DamageInfo(damageInfo.Attacker.GetComponent<Component>(),damageInfo.Damage, damageInfo.Weapon.GetComponent<Component>(),damageInfo.Position, force, tags);
	}
}
