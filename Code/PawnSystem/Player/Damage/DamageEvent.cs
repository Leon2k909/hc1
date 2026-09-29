using Sandbox.Events;

namespace Facepunch;

[Flags]
public enum HitboxTags
{
	None = 0,
	Head = 1,
	Chest = 2,
	Stomach = 4,
	Clavicle = 8,
	Arm = 16,
	Hand = 32,
	Leg = 64,
	Ankle = 128,
	Spine = 256,
	Neck = 512,

	UpperBody = Neck | Chest | Clavicle,
	LowerBody = Stomach
}

[Flags]
public enum DamageFlags
{
	None = 0,

	/// <summary>
	/// The victim was wearing kevlar.
	/// </summary>
	Armor = 1,

	/// <summary>
	/// The victim was wearing a helmet.
	/// </summary>
	Helmet = 2,

	/// <summary>
	/// This was a knife attack.
	/// </summary>
	Melee = 4,

	/// <summary>
	/// This was some kind of explosion.
	/// </summary>
	Explosion = 8,

	/// <summary>
	/// The victim fell.
	/// </summary>
	FallDamage = 16,
	
	/// <summary>
	/// The victim was burned.
	/// </summary>
	Burn = 32,

	/// <summary>
	/// Did the attacker shoot through a wall?
	/// </summary>
	WallBang = 64,

	/// <summary>
	/// Was the attacker in the air when doing this damage?
	/// </summary>
	AirShot = 128,

	/// <summary>
	/// The battle royale's closing zone (<see cref="SafeZoneManager"/>): steady damage with no hit location, never a
	/// hardcore one-shot.
	/// </summary>
	Zone = 256,
}

/// <summary>
/// Event dispatched when a <see cref="HealthComponent"/> takes damage.
/// </summary>
/// <param name="Attacker">Who was the attacker?</param>
/// <param name="Damage">How much damage?</param>
/// <param name="Inflictor">What caused this damage? Can be a weapon, grenade, etc.</param>
/// <param name="Position">The point of the damage. Normally where you were hit.</param>
/// <param name="Force">The force of the damage.</param>
/// <param name="Hitbox">What hitbox did we hit?</param>
/// <param name="Flags">Extra data that we can pass around. Like if it's a blind-shot, mid-air shot, through smoke shot, etc.</param>
/// <param name="ArmorDamage">How much armor damage?</param>
/// <param name="RemoveHelmet">Did this damage remove the victim's helmet?</param>
public record DamageInfo( Component Attacker, float Damage, Component Inflictor = null,
	Vector3 Position = default, Vector3 Force = default,
	HitboxTags Hitbox = default, DamageFlags Flags = DamageFlags.None,
	float ArmorDamage = 0f, bool RemoveHelmet = false )
{
	/// <summary>
	/// Who took damage?
	/// </summary>
	public Component Victim { get; init; }

	/// <inheritdoc cref="DamageFlags.Armor"/>
	public bool HasArmor => Flags.HasFlag( DamageFlags.Armor );

	/// <inheritdoc cref="DamageFlags.Helmet"/>
	public bool HasHelmet => Flags.HasFlag( DamageFlags.Helmet );

	/// <inheritdoc cref="DamageFlags.Helmet"/>
	public bool WasMelee => Flags.HasFlag( DamageFlags.Melee );

	/// <inheritdoc cref="DamageFlags.Explosion"/>
	public bool WasExplosion => Flags.HasFlag( DamageFlags.Explosion );

	/// <inheritdoc cref="DamageFlags.FallDamage"/>
	public bool WasFallDamage => Flags.HasFlag( DamageFlags.FallDamage );

	/// <summary>
	/// How long since this damage info event happened?
	/// </summary>
	public RealTimeSince TimeSinceEvent { get; init; } = 0;

	public override string ToString()
	{
		return $"\"{Attacker}\" - \"{Victim}\" with \"{Inflictor}\" ({Damage} damage)";
	}
}

/// <summary>
/// Event dispatched on the host when something takes damage, so it can be modified.
/// </summary>
public abstract class ModifyDamageEvent : IGameEvent
{
	public DamageInfo DamageInfo { get; set; }

	/// <summary>
	/// Clears all health and armor damage from this event.
	/// </summary>
	public void ClearDamage()
	{
		DamageInfo = DamageInfo with { Damage = 0f, ArmorDamage = 0f, RemoveHelmet = false };
	}

	/// <summary>
	/// Scales health damage by the given multiplier.
	/// </summary>
	public void ScaleDamage( float scale )
	{
		DamageInfo = DamageInfo with { Damage = DamageInfo.Damage * scale };
	}

	/// <summary>
	/// Flag that the victim's helmet should be removed when this damage is applied.
	/// </summary>
	public void RemoveHelmet()
	{
		DamageInfo = DamageInfo with { RemoveHelmet = true };
	}

	/// <summary>
	/// Scales <see cref="DamageInfo.Damage"/> by <paramref name="damageScale"/>, adding the difference to <see cref="DamageInfo.ArmorDamage"/>.
	/// </summary>
	public void ApplyArmor( float damageScale )
	{
		var reduced = DamageInfo.Damage * damageScale;

		DamageInfo = DamageInfo with { Damage = reduced, ArmorDamage = DamageInfo.Damage - reduced };
	}

	/// <summary>
	/// Adds a flag to this damage event.
	/// </summary>
	/// <param name="flag"></param>
	public void AddFlag( DamageFlags flag )
	{
		DamageInfo = DamageInfo with { Flags = DamageInfo.Flags | flag };
	}

	/// <summary>
	/// Removes a flag from this damage event.
	/// </summary>
	/// <param name="flag"></param>
	public void WithoutFlag( DamageFlags flag )
	{
		DamageInfo = DamageInfo with { Flags = DamageInfo.Flags & flag };
	}
}

/// <summary>
/// Event dispatched on the host when this object is about to take damage, so it can be modified.
/// </summary>
public class ModifyDamageTakenEvent : ModifyDamageEvent
{
}

/// <summary>
/// Event dispatched on the host when this object is about to deal damage, so it can be modified.
/// </summary>
public class ModifyDamageGivenEvent : ModifyDamageEvent
{
}

/// <summary>
/// Event dispatched on the host when any object is about to deal damage, so it can be modified.
/// </summary>
public class ModifyDamageGlobalEvent : ModifyDamageEvent
{

}

/// <summary>
/// Event dispatched on a root object containing a <see cref="HealthComponent"/> that took damage.
/// </summary>
/// <param name="Damage">Information about the damage.</param>
public record DamageTakenEvent( DamageInfo DamageInfo ) : IGameEvent;

/// <summary>
/// Event dispatched to everything when a <see cref="HealthComponent"/> takes damage.
/// </summary>
/// <param name="DamageInfo"></param>
public record DamageTakenGlobalEvent ( DamageInfo DamageInfo ) : IGameEvent;

/// <summary>
/// Event dispatched on a root object that inflicted damage on another object.
/// </summary>
/// <param name="Damage">Information about the damage.</param>
public record DamageGivenEvent( DamageInfo DamageInfo ) : IGameEvent;

/// <summary>
/// Event dispatched in the scene when a <see cref="HealthComponent"/> died after taking damage.
/// </summary>
/// <param name="Damage">Information about the killing blow.</param>
public record KillEvent( DamageInfo DamageInfo ) : IGameEvent;

public static class SceneTraceExtensions
{
	public static HitboxTags GetHitboxTags( this SceneTraceResult tr ) => tr.Hitbox.GetHitboxTags();

	private static Surface _wood;

	/// <summary>
	/// The surface a hit looks and sounds like. Map clutter's collision (Ridgeback's trees) comes with the default
	/// surface, which chips like concrete, so it counts as wood.
	/// </summary>
	public static Surface GetImpactSurface( this SceneTraceResult tr )
	{
		if ( tr.Shape is { } shape && shape.Tags.Has( "clutter" ) && tr.Surface?.ResourceName is null or "default" )
			return _wood ??= ResourceLibrary.Get<Surface>( "surfaces/wood.surface" ) ?? tr.Surface;

		return tr.Surface;
	}

	private const HitboxTags Limbs = HitboxTags.Arm | HitboxTags.Hand | HitboxTags.Leg | HitboxTags.Ankle;
	private const HitboxTags Vitals = HitboxTags.Head | HitboxTags.Neck | HitboxTags.Chest | HitboxTags.Stomach
		| HitboxTags.Clavicle | HitboxTags.Spine;

	/// <summary>
	/// Where a bullet that reached this body really hit it. A box trace touches hitboxes the bullet's line only passed
	/// near (the other leg), and a round goes through an arm held across the body and on into the chest. So this follows
	/// the line through the body and takes the first vital hitbox on it, else the first limb. A near miss that only the
	/// box touched keeps its hitbox.
	/// </summary>
	public static SceneTraceResult ThroughBody( this SceneTraceResult tr, Scene scene )
	{
		var root = tr.GameObject?.Root;
		if ( tr.Hitbox is null || root is null )
			return tr;

		var line = scene.Trace.Ray( tr.EndPosition - tr.Direction * 32f, tr.EndPosition + tr.Direction * 96f )
			.UseHitboxes()
			.WithoutTags( "trigger", "playerclip", "movement" )
			.RunAll();

		SceneTraceResult limb = default;
		foreach ( var hit in line )
		{
			if ( !hit.Hit || hit.Hitbox is null || hit.GameObject?.Root != root )
				continue;

			var tags = hit.GetHitboxTags();
			if ( (tags & Vitals) != 0 || (tags & Limbs) == 0 )
				return hit;

			if ( !limb.Hit )
				limb = hit;
		}

		return limb.Hit ? limb : tr;
	}

	public static HitboxTags GetHitboxTags( this Hitbox hitbox )
	{
		if ( hitbox is null ) return HitboxTags.None;

		var tags = HitboxTags.None;

		foreach ( var tag in hitbox.Tags )
		{
			if ( Enum.TryParse<HitboxTags>( tag, true, out var hitboxTag ) )
			{
				tags |= hitboxTag;
			}
		}

		return tags != HitboxTags.None ? tags : FromBoneName( hitbox.Bone?.Name );
	}

	/// <summary>
	/// The player models' leg, pelvis and clavicle hitboxes have no tags (or only "pelvis", which isn't one of ours), so
	/// the bone says where the hit was.
	/// </summary>
	private static HitboxTags FromBoneName( string bone )
	{
		if ( string.IsNullOrEmpty( bone ) ) return HitboxTags.None;

		bone = bone.ToLowerInvariant();
		bool Has( params string[] parts ) => parts.Any( bone.Contains );

		if ( Has( "head" ) ) return HitboxTags.Head;
		if ( Has( "neck" ) ) return HitboxTags.Neck;
		if ( Has( "clavicle" ) ) return HitboxTags.Clavicle;
		if ( Has( "spine", "chest" ) ) return HitboxTags.Chest;
		if ( Has( "pelvis" ) ) return HitboxTags.Stomach;
		if ( Has( "foot", "ankle", "toe" ) ) return HitboxTags.Ankle;
		if ( Has( "hip", "thigh", "knee", "calf", "leg" ) ) return HitboxTags.Leg;
		if ( Has( "hand", "finger", "thumb", "wrist" ) ) return HitboxTags.Hand;
		if ( Has( "arm", "elbow", "shoulder" ) ) return HitboxTags.Arm;
		return HitboxTags.None;
	}
}
