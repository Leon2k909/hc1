namespace Facepunch;

/// <summary>Deterministic regional trauma for hardcore. No bleeding or random fatal-hit rolls.</summary>
public partial class HealthComponent
{
	private const HitboxTags HeadOrNeck = HitboxTags.Head | HitboxTags.Neck;
	private const HitboxTags Body = HeadOrNeck | HitboxTags.Chest | HitboxTags.Stomach | HitboxTags.Clavicle | HitboxTags.Spine;
	private const HitboxTags Chest = HitboxTags.Chest | HitboxTags.Clavicle | HitboxTags.Spine;
	private const HitboxTags Legs = HitboxTags.Leg | HitboxTags.Ankle;
	private const HitboxTags Arms = HitboxTags.Arm | HitboxTags.Hand;

	/// <summary>A limb hit takes this times the round's damage: 34 for an M4 (20), so three kill. At most half your health.</summary>
	public const float LimbWoundScale = 1.7f;

	/// <summary>How much slower each leg wound makes every gait (up to two count).</summary>
	public const float LegWoundSlowdown = 0.15f;

	/// <summary>A shot leg starts to come good this long after the last leg hit...</summary>
	public const float LegWoundRecoverDelay = 1.5f;

	/// <summary>...then heals this many wounds a second: one hit has worn off about 3 s after it landed, two about 5 s.</summary>
	public const float LegWoundRecoverRate = 0.6f;

	/// <summary>How much more each arm wound makes the gun kick (up to two count).</summary>
	public const float ArmWoundRecoil = 0.25f;

	/// <summary>How lame the legs are: one per leg or foot hit or hard landing (up to two), healing back to none (see OnFixedUpdate).</summary>
	[Sync( SyncFlags.FromHost )] public float LegWounds { get; private set; }

	private TimeSince _timeSinceLegWound;

	/// <summary>How many times this life's arms or hands have been shot.</summary>
	[Sync( SyncFlags.FromHost )] public int ArmWounds { get; private set; }

	/// <summary>Scales every gait's speed for <see cref="LegWounds"/>.</summary>
	public float WoundSpeedScale => 1f - LegWoundSlowdown * Math.Min( LegWounds, 2f );

	/// <summary>Scales recoil for <see cref="ArmWounds"/>.</summary>
	public float WoundRecoilScale => 1f + ArmWoundRecoil * Math.Min( ArmWounds, 2 );

	public void ClearWounds()
	{
		LegWounds = 0;
		ArmWounds = 0;
	}

	/// <summary>Explosions, knives and falls don't pick a hit location (see <see cref="WithThisAsVictim"/>).</summary>
	private static bool IsBulletHit( DamageInfo damageInfo ) =>
		!damageInfo.WasExplosion && !damageInfo.WasMelee && !damageInfo.WasFallDamage
		&& !damageInfo.Flags.HasFlag( DamageFlags.Burn ) && !damageInfo.Flags.HasFlag( DamageFlags.Zone );

	/// <summary>An arm or leg and nothing vital. A hit with no hitbox counts as the body.</summary>
	private static bool IsLimbHit( DamageInfo damageInfo ) =>
		IsBulletHit( damageInfo ) && (damageInfo.Hitbox & Body) == 0 && (damageInfo.Hitbox & (Legs | Arms)) != 0;

	/// <summary>
	/// A hardcore bullet's damage by where it hit (see the class summary). <paramref name="gunDamage"/> is the round's
	/// damage before hitbox scaling and armor, after falloff.
	/// </summary>
	private DamageInfo HardcoreBullet( DamageInfo damageInfo, float gunDamage, out bool lethal )
	{
		// Armor was previously applied and then discarded here. Preserve coverage and
		// weapon-specific protection; do not apply the core hitbox multipliers twice.
		var total = damageInfo.Damage + damageInfo.ArmorDamage;
		var transmission = total > 0f ? Math.Clamp( damageInfo.Damage / total, 0f, 1f ) : 1f;
		var region = (damageInfo.Hitbox & HeadOrNeck) != 0 ? TraumaRegion.Head
			: IsLimbHit( damageInfo ) ? TraumaRegion.Limb
			: (damageInfo.Hitbox & HitboxTags.Stomach) != 0 && (damageInfo.Hitbox & Chest) == 0
				? TraumaRegion.Abdomen : TraumaRegion.Chest;
		var trauma = HardcoreTrauma.Damage( gunDamage, region, MaxHealth );
		lethal = false;
		return damageInfo with { Damage = trauma * transmission, ArmorDamage = trauma * (1f - transmission) };
	}

	private void AddWound( HitboxTags hitbox )
	{
		if ( (hitbox & Legs) != 0 )
		{
			LegWounds = Math.Min( LegWounds + 1f, 2f );
			_timeSinceLegWound = 0f;
		}

		if ( (hitbox & Arms) != 0 ) ArmWounds++;
	}

	protected override void OnFixedUpdate()
	{
		// Host: leg slowing eases off after the last hit in every ruleset.
		if ( !Networking.IsHost || LegWounds <= 0f || _timeSinceLegWound < LegWoundRecoverDelay ) return;

		LegWounds = Math.Max( 0f, LegWounds - LegWoundRecoverRate * Time.Delta );
	}
}
