namespace Facepunch.Gunsmith;

/// <summary>
/// Effects that the current firearm model can represent. These are relative to the
/// weapon prefab, so a fitted part never changes cartridge damage. It changes the fire rate only where
/// the real part does: a different gas system length (<see cref="FireRate"/>), or suppressor
/// back-pressure (<see cref="Shootable.SuppressorFireRateScale"/>, which depends on the action).
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
			FireRate = 1f
		};

		// Loadout cookies are local to the shooter. The owner computes shot effects
		// and broadcasts the chosen visual result to everyone else.
		if ( !equipment.IsValid() || !equipment.ApplySavedAttachments || !equipment.Resource.IsValid()
			|| !equipment.Owner.IsValid() || !equipment.Owner.IsLocallyControlled )
			return effects;

		var prone = equipment.Owner.IsProne;
		ApplySelected( ref effects, equipment.Resource, GunsmithPartType.Muzzle, prone );
		ApplySelected( ref effects, equipment.Resource, GunsmithPartType.Barrel, prone );
		ApplySelected( ref effects, equipment.Resource, GunsmithPartType.Stock, prone );
		ApplySelected( ref effects, equipment.Resource, GunsmithPartType.Underbarrel, prone );
		ApplySelected( ref effects, equipment.Resource, GunsmithPartType.RearGrip, prone );

		return effects;
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

		if ( (part.Category is GunsmithPartType.Muzzle or GunsmithPartType.Barrel)
			&& (part.IsSuppressor || Has( "suppressor" ) || Has( "silencer" )) )
		{
			// Gas and added muzzle mass soften recoil; the report still exists. The can adds a little
			// effective barrel length, so the bullet leaves slightly faster.
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
