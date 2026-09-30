namespace Facepunch.Gunsmith;

/// <summary>
/// Effects that the current firearm model can represent. These are relative to the
/// weapon prefab, so a fitted part never changes cartridge damage. It changes the fire rate only where
/// the real part does: a different gas system length or a heavier or lighter AR buffer (<see cref="FireRate"/>), or
/// suppressor back-pressure (<see cref="Shootable.SuppressorFireRateScale"/>, which depends on the action, and which a
/// gas regulator's suppressed setting takes away: <see cref="SuppressedGas"/>).
/// <para>
/// Every part's weight counts too (<see cref="GunsmithPart.Mass"/>, <see cref="ApplyMass"/>): a heavier gun kicks less,
/// but it's slower to bring up to the eye and to carry.
/// </para>
/// </summary>
public struct GunsmithAttachmentEffects
{
	public float VerticalRecoil { get; private set; }
	public float HorizontalRecoil { get; private set; }
	public float DamageFalloffDistance { get; private set; }
	public float FlashChance { get; private set; }
	public float HearingDistance { get; private set; }
	public float SoundVolume { get; private set; }
	public float FireRate { get; private set; }
	/// <summary> A fitted gas regulator is on its suppressed setting (<see cref="GunsmithPart.SuppressedGasSetting"/>). </summary>
	public bool SuppressedGas { get; private set; }
	/// <summary> What the fitted parts add to the gun's loaded weight, in kg (negative if they take weight off). </summary>
	public float Mass { get; private set; }
	/// <summary> The gun's loaded weight with its parts, in kg (0 before <see cref="ApplyMass"/>). </summary>
	public float LoadedMass { get; private set; }
	/// <summary> Aiming-in time against the factory gun's, from the parts' weight. </summary>
	public float AimTime { get; private set; }
	/// <summary>
	/// How much more the parts' weight slows every gait, added to <see cref="Equipment.WeightSlowdown"/> (0.01 = 1% slower).
	/// </summary>
	public float WeightSlowdown { get; private set; }

	/// <summary> The AKM's 3.75 kg, loaded: the weight the rifles' speeds and aiming time are set for. </summary>
	public const float ReferenceMass = 3.75f;
	/// <summary>
	/// About what a soldier's arms add to the weight they swing up to the eye, in kg. Aiming in takes time as the square
	/// root of the moving weight (a fixed push moves a heavier load more slowly), which is how the RPK's 0.3 s is set
	/// against the rifles' 0.25 s.
	/// </summary>
	public const float ArmsMass = 4f;
	/// <summary> Every gait slows by about 1% per kg carried over the rifles' weight (Hunt et al., 2016). </summary>
	public const float SlowdownPerKg = 0.01f;

	/// <summary> The categories whose parts have effects, weight included. Charms, camos and stickers weigh next to nothing. </summary>
	private static readonly GunsmithPartType[] EffectSlots =
	{
		GunsmithPartType.Muzzle, GunsmithPartType.Barrel, GunsmithPartType.Stock, GunsmithPartType.Underbarrel,
		GunsmithPartType.RearGrip, GunsmithPartType.Action, GunsmithPartType.Optic, GunsmithPartType.Magazine,
		GunsmithPartType.Laser, GunsmithPartType.Rail, GunsmithPartType.Ammunition
	};

	public static GunsmithAttachmentEffects For( Equipment equipment )
	{
		var effects = new GunsmithAttachmentEffects
		{
			VerticalRecoil = 1f,
			HorizontalRecoil = 1f,
			DamageFalloffDistance = 1f,
			FlashChance = 1f,
			HearingDistance = 1f,
			SoundVolume = 1f,
			FireRate = 1f,
			AimTime = 1f
		};

		// Loadout cookies are local to the shooter. The owner computes shot effects
		// and broadcasts the chosen visual result to everyone else.
		if ( !equipment.IsValid() || !equipment.ApplySavedAttachments || !equipment.Resource.IsValid()
			|| !equipment.Owner.IsValid() || !equipment.Owner.IsLocallyControlled )
			return effects;

		var prone = equipment.Owner.IsProne;
		foreach ( var slot in EffectSlots )
			ApplySelected( ref effects, equipment.Resource, slot, prone );

		effects.ApplyMass( equipment.LoadedMass );
		return effects;
	}

	/// <summary>
	/// The effects of the parts saved for <paramref name="resource"/> in the active class, standing (a bipod only
	/// helps prone). For the gunsmith's stats, which have no equipment or owner.
	/// </summary>
	public static GunsmithAttachmentEffects ForBuild( EquipmentResource resource )
	{
		var effects = new GunsmithAttachmentEffects
		{
			VerticalRecoil = 1f,
			HorizontalRecoil = 1f,
			DamageFalloffDistance = 1f,
			FlashChance = 1f,
			HearingDistance = 1f,
			SoundVolume = 1f,
			FireRate = 1f,
			AimTime = 1f
		};

		if ( !resource.IsValid() )
			return effects;

		foreach ( var slot in EffectSlots )
			ApplySelected( ref effects, resource, slot, false );

		effects.ApplyMass( GunMass( resource ) );
		return effects;
	}

	/// <summary> <paramref name="resource"/>'s loaded weight from its prefab's <see cref="Equipment.LoadedMass"/>, else 0. </summary>
	public static float GunMass( EquipmentResource resource )
	{
		var equipment = resource?.MainPrefab?.GetComponent<Equipment>( true );
		return equipment.IsValid() ? equipment.LoadedMass : 0f;
	}

	/// <summary>
	/// What the fitted parts' weight does to a gun that weighs <paramref name="gunMass"/> kg loaded (0: not known, taken as
	/// <see cref="ReferenceMass"/>).
	/// <list type="bullet">
	/// <item>Recoil: the same round kicks a heavier gun back more slowly (free recoil goes as one over the weight), so it's
	/// scaled by the gun's weight over the gun's with its parts.</item>
	/// <item>Aiming in: as the square root of the weight swung up with the arms (<see cref="ArmsMass"/>).</item>
	/// <item>Moving: <see cref="SlowdownPerKg"/> for each kg over <see cref="ReferenceMass"/>, as a heavy gun's own
	/// <see cref="Equipment.WeightSlowdown"/> is set. A gun under it doesn't get faster than the rifles.</item>
	/// </list>
	/// </summary>
	private void ApplyMass( float gunMass )
	{
		var gun = gunMass > 0f ? gunMass : ReferenceMass;
		var total = MathF.Max( gun + Mass, gun * 0.5f );
		LoadedMass = total;
		if ( Mass == 0f )
			return;

		var recoil = gun / total;
		VerticalRecoil *= recoil;
		HorizontalRecoil *= recoil;
		AimTime = MathF.Sqrt( (total + ArmsMass) / (gun + ArmsMass) );
		WeightSlowdown = SlowdownPerKg * (MathF.Max( total, ReferenceMass ) - MathF.Max( gun, ReferenceMass ));
	}

	private static void ApplySelected( ref GunsmithAttachmentEffects effects, EquipmentResource resource,
		GunsmithPartType category, bool prone )
	{
		if ( GunsmithLoadoutManager.TryGetAttachment( resource, category, out var part ) && part.IsValid() )
			effects.Apply( part, prone );
	}

	private void Apply( GunsmithPart part, bool prone )
	{
		var name = part.Name ?? string.Empty;
		bool Has( string word ) => name.Contains( word, System.StringComparison.OrdinalIgnoreCase );

		VerticalRecoil *= part.VerticalRecoilScale;
		HorizontalRecoil *= part.HorizontalRecoilScale;
		if ( part.DamageFalloffScale > 0f ) DamageFalloffDistance *= part.DamageFalloffScale;
		if ( part.FireRateScale > 0f ) FireRate *= part.FireRateScale;
		if ( part.SuppressedGasSetting ) SuppressedGas = true;
		Mass += part.Mass;

		if ( (part.Category is GunsmithPartType.Muzzle or GunsmithPartType.Barrel)
			&& (part.IsSuppressor || Has( "suppressor" ) || Has( "silencer" )) )
		{
			// The can traps the muzzle gas, whose jet otherwise adds to the kick (its weight counts through Mass); the
			// report still exists. The can adds a little effective barrel length, so the bullet leaves slightly faster.
			VerticalRecoil *= 0.94f;
			HorizontalRecoil *= 0.94f;
			HearingDistance *= 0.20f;
			DamageFalloffDistance *= 1.02f;
		}

		switch ( part.Category )
		{
			case GunsmithPartType.Muzzle:
				if ( Has( "muzzle brake" ) )
				{
					// Side ports push against rearward recoil, with more side blast.
					VerticalRecoil *= 0.82f;
					HorizontalRecoil *= 0.80f;
					FlashChance *= 1.2f;
					HearingDistance *= 1.15f;
					SoundVolume *= 1.1f;
				}
				else if ( Has( "compensator" ) )
				{
					// Upward gas vents counter muzzle climb more than rearward kick.
					VerticalRecoil *= 0.75f;
					HorizontalRecoil *= 0.95f;
					FlashChance *= 1.1f;
					SoundVolume *= 1.05f;
				}
				else if ( Has( "flash guard" ) || Has( "flash hider" ) )
				{
					FlashChance *= 0.18f;
				}
				break;

			case GunsmithPartType.Barrel:
				// Barrel length affects velocity and therefore the distance at which
				// damage falls off. It does not change the cartridge's close-range hit.
				if ( Has( "7.5\"" ) ) DamageFalloffDistance *= 0.78f;
				else if ( Has( "11.5\"" ) || Has( "short barrel" ) ) DamageFalloffDistance *= 0.88f;
				else if ( Has( "20\"" ) || Has( "long" ) || Has( "419mm" ) ) DamageFalloffDistance *= 1.12f;
				else if ( Has( "recon barrel" ) ) DamageFalloffDistance *= 1.06f;

				// The AR barrels also change the gas system relative to the 14.5" carbine: the port sits
				// closer to the chamber on short barrels (higher pressure, faster cycling, like the Mk18)
				// and further along on mid-length and rifle-length ones (M16 cycles slower than the M4).
				if ( Has( "7.5\"" ) ) FireRate *= 1.12f;
				else if ( Has( "11.5\"" ) ) FireRate *= 1.07f;
				else if ( Has( "20\"" ) ) FireRate *= 0.90f;
				else if ( Has( "419mm" ) ) FireRate *= 0.95f;
				break;

			case GunsmithPartType.Stock:
				if ( Has( "no stock" ) || Has( "buffer tube" ) )
				{
					VerticalRecoil *= 1.25f;
					HorizontalRecoil *= 1.25f;
				}
				else if ( Has( "precision" ) || Has( "full stock" ) || Has( "stalker" ) )
				{
					VerticalRecoil *= 0.90f;
					HorizontalRecoil *= 0.90f;
				}
				else if ( Has( "collapsible" ) || Has( "ultralight" ) )
				{
					VerticalRecoil *= 1.05f;
					HorizontalRecoil *= 1.05f;
				}
				break;

			case GunsmithPartType.Underbarrel:
				if ( Has( "bipod" ) )
				{
					// The game has no deploy action; prone is the supported brace.
					if ( prone )
					{
						VerticalRecoil *= 0.65f;
						HorizontalRecoil *= 0.65f;
					}
				}
				else if ( Has( "angled" ) || Has( "commando foregrip" ) || Has( "tactical foregrip" ) )
					HorizontalRecoil *= 0.91f;
				else if ( Has( "grip" ) )
					VerticalRecoil *= 0.91f;
				break;

			case GunsmithPartType.RearGrip:
				if ( Has( "rubber" ) || Has( "support" ) )
				{
					VerticalRecoil *= 0.96f;
					HorizontalRecoil *= 0.96f;
				}
				break;
		}
	}

	public static string Describe( GunsmithPart part )
	{
		if ( !part.IsValid() ) return null;
		var name = part.Name ?? string.Empty;
		bool Has( string word ) => name.Contains( word, System.StringComparison.OrdinalIgnoreCase );
		if ( (part.Category is GunsmithPartType.Muzzle or GunsmithPartType.Barrel)
			&& (part.IsSuppressor || Has( "suppressor" ) || Has( "silencer" )) )
			return "Quieter report, less flash, slightly less recoil; back-pressure speeds up gas-operated actions";
		if ( part.Category == GunsmithPartType.Muzzle )
		{
			if ( Has( "muzzle brake" ) ) return "Less recoil; louder muzzle blast";
			if ( Has( "compensator" ) ) return "Less muzzle climb; more flash";
			if ( Has( "flash guard" ) || Has( "flash hider" ) ) return "Less visible muzzle flash";
		}
		if ( part.Category == GunsmithPartType.Barrel )
		{
			if ( Has( "7.5\"" ) || Has( "11.5\"" ) ) return "Earlier damage falloff at distance; shorter gas system fires faster";
			if ( Has( "short barrel" ) ) return "Earlier damage falloff at distance";
			if ( Has( "20\"" ) || Has( "419mm" ) ) return "Later damage falloff at distance; longer gas system fires slower";
			if ( Has( "long" ) || Has( "recon barrel" ) ) return "Later damage falloff at distance";
		}
		if ( part.Category == GunsmithPartType.Stock )
		{
			if ( Has( "no stock" ) || Has( "buffer tube" ) ) return "Less shoulder support; more recoil";
			if ( Has( "precision" ) || Has( "full stock" ) || Has( "stalker" ) ) return "More shoulder support; less recoil";
			if ( Has( "collapsible" ) || Has( "ultralight" ) ) return "Lighter support; slightly more recoil";
		}
		if ( part.Category == GunsmithPartType.Underbarrel )
		{
			if ( Has( "bipod" ) ) return "Reduces recoil while prone";
			if ( Has( "angled" ) || Has( "commando foregrip" ) || Has( "tactical foregrip" ) ) return "Improves horizontal recoil control";
			if ( Has( "grip" ) ) return "Improves vertical recoil control";
		}
		if ( part.Category == GunsmithPartType.RearGrip && (Has( "rubber" ) || Has( "support" )) )
			return "Slightly improves recoil control";
		return null;
	}
}
