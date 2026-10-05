namespace Facepunch;

/// <summary>
/// Hardcore bullets go by where they hit, the same for players and bots. The head or neck kills. The body is a chance
/// to kill outright (a hit to the heart, a major vessel or the spine), better the harder the round hits, and otherwise a
/// heavy wound, so a rifle's second body hit kills unless you've healed in between. Three rifle hits to the arms or legs
/// kill (more for pistols and SMGs); a shot leg or foot slows you down for a few seconds and a shot arm or hand makes
/// the gun harder to hold steady until you die (health comes back, see PlayerPawn.UpdateHealthRegen). Everything scales
/// with the round's damage after falloff, so a stray shotgun pellet at range is a scratch. A landing hard enough to hurt
/// lames the legs like a leg hit, in every mode (see TakeDamage).
/// </summary>
public partial class HealthComponent
{
	private const HitboxTags HeadOrNeck = HitboxTags.Head | HitboxTags.Neck;
	private const HitboxTags Body = HeadOrNeck | HitboxTags.Chest | HitboxTags.Stomach | HitboxTags.Clavicle | HitboxTags.Spine;
	private const HitboxTags Chest = HitboxTags.Chest | HitboxTags.Clavicle | HitboxTags.Spine;
	private const HitboxTags Legs = HitboxTags.Leg | HitboxTags.Ankle;
	private const HitboxTags Arms = HitboxTags.Arm | HitboxTags.Hand;

	/// <summary>A limb hit takes this times the round's damage: 34 for an M4 (20), so three kill. At most half your health.</summary>
	public const float LimbWoundScale = 1.7f;

	/// <summary>A body hit that doesn't kill outright takes this times the round's damage: 60 for an M4, so two kill.</summary>
	public const float BodyWoundScale = 3f;

	/// <summary>
	/// The chance a body hit kills outright is the round's damage over this: an M4's (20) half the time, a pistol's (15)
	/// 37%, a shotgun pellet's (8) 20%, the M700's nearly always (<see cref="MaxBodyKillChance"/>). At 100 health; a
	/// custom game's other health scales it inversely.
	/// </summary>
	public const float BodyKillDamage = 40f;
	public const float MaxBodyKillChance = 0.95f;

	/// <summary>A gut or pelvis hit is less often instantly fatal than one to the chest.</summary>
	public const float AbdomenKillChanceScale = 0.6f;

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
		var hitbox = damageInfo.Hitbox;
		lethal = false;

		if ( IsLimbHit( damageInfo ) )
			return damageInfo with { Damage = MathF.Min( gunDamage * LimbWoundScale, MaxHealth * 0.5f ) };

		if ( (hitbox & HeadOrNeck) != 0 )
		{
			lethal = true;
		}
		else
		{
			// More health (a custom game's) makes a body hit less often fatal, less makes it more: 50% for an M4 at 100,
			// 25% at 200.
			var toughness = MaxHealth > 0f ? CustomGameRules.DefaultMaxHealth / MaxHealth : 1f;
			var chance = Math.Min( gunDamage / BodyKillDamage * toughness, MaxBodyKillChance );
			if ( (hitbox & HitboxTags.Stomach) != 0 && (hitbox & Chest) == 0 )
				chance *= AbdomenKillChanceScale;

			lethal = Game.Random.Float() < chance;
			if ( !lethal )
				return damageInfo with { Damage = gunDamage * BodyWoundScale };
		}

		return damageInfo with { Damage = MaxHealth };
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
		// Host: a shot leg eases off once it hasn't been hit again for a moment, players and bots alike.
		if ( !Networking.IsHost || LegWounds <= 0f || _timeSinceLegWound < LegWoundRecoverDelay ) return;

		LegWounds = Math.Max( 0f, LegWounds - LegWoundRecoverRate * Time.Delta );
	}
}
