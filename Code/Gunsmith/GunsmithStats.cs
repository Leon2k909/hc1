namespace Facepunch.Gunsmith;

/// <summary>
/// The gunsmith's stat bars, read from the weapon's prefabs the way the game uses them when it fires, with the active
/// class's parts (<see cref="GunsmithAttachmentEffects.ForBuild"/>) and the weapon's tuning applied. Every bar is on one
/// fixed scale for all guns, so they compare:
/// - Damage: one shot (every pellet of a shotgun's) out of 50.
/// - Fire rate: out of 1000 rpm.
/// - Handling: aim-down-sights time, from 0.5 s (empty) to 0.15 s (full). The game has no spread or bloom to rate, so
///   this takes the place CoD gives accuracy.
/// - Mobility: walk speed with the gun out, from 70% to 95% of unarmed.
/// - Range: where a hit still does 80% of its damage, out of 150 m. Guns with no falloff are full.
/// - Control: the mean kick per shot, where <see cref="NoControlKick"/> is none.
/// </summary>
public sealed record GunsmithStats
{
	/// <summary> PlayerGlobals' default walk speed, which each gun's SpeedPenalty comes off. </summary>
	private const float WalkSpeed = 220f;

	/// <summary> PlayerGlobals' other gaits (no scene sets its own): sprinting takes half the gun's SpeedPenalty off. </summary>
	private const float SprintSpeed = 260f;
	private const float CrouchSpeed = 100f;
	private const float ProneSpeed = 50f;

	/// <summary> A MaxRange this long is a gun with no damage falloff (pistols, the M700, the shotgun). </summary>
	private const float NoFalloffRange = 100000f;

	/// <summary> The mean kick (as ShootRecoil adds it) that rates 0 control. The Kastov 762, the hardest-kicking rifle, kicks 16. </summary>
	private const float NoControlKick = 25f;

	private const float InchesToMeters = 0.0254f;

	/// <summary> False for equipment that doesn't shoot (knives, grenades): the gunsmith shows no bars for it. </summary>
	public bool IsFirearm { get; init; }

	public float Damage { get; init; }
	public string DamageText { get; init; } = "";
	public float FireRate { get; init; }
	public string FireRateText { get; init; } = "";
	public float Handling { get; init; }
	public string HandlingText { get; init; } = "";
	public float Mobility { get; init; }
	public string MobilityText { get; init; } = "";
	public float Range { get; init; }
	public string RangeText { get; init; } = "";
	public float Control { get; init; }
	public string ControlText { get; init; } = "";

	public int Rounds { get; init; }
	public string FireModeText { get; init; } = "";

	/// <summary> <see cref="FireModeText"/> in the player's language, each of "AUTO / BURST / SEMI" on its own. </summary>
	public string FireModeShown => string.Join( " / ", FireModeText.Split( " / " ).Select( x => Tr( x ) ) );

	// The real figures behind the bars, for the advanced stats (WeaponComparePanel).

	/// <summary> One bullet's (or pellet's) damage before falloff. </summary>
	public float BulletDamage { get; init; }
	public int Pellets { get; init; } = 1;
	public float Rpm { get; init; }
	/// <summary> Aim-down-sights time, seconds. </summary>
	public float AimTime { get; init; }
	/// <summary> Reload times in seconds; for a gun loaded a round at a time (<see cref="SingleReload"/>), per round. </summary>
	public float ReloadTime { get; init; }
	public float EmptyReloadTime { get; init; }
	public bool SingleReload { get; init; }
	/// <summary> Spare rounds carried, not counting the magazine. </summary>
	public int Reserve { get; init; }
	/// <summary> Metres at which a hit still does 80% of its damage; null with no falloff. </summary>
	public float? FullDamageRange { get; init; }
	/// <summary> Metres per second (Warzone's bullet drop uses it); 0 if the gun has none set. </summary>
	public float MuzzleVelocity { get; init; }
	/// <summary>
	/// One bullet's (or pellet's) damage where it hits at 10, 25, 50, 100 and 200 m, down the falloff curve as
	/// Shootable.CalculateDamageFalloff works it out; 0 past MaxRange, where the shot's trace ends.
	/// </summary>
	public (float At10, float At25, float At50, float At100, float At200) RangeDamage { get; init; }
	/// <summary> The mean kick of one shot up and to the side, each out of the kick that rates 0 control. </summary>
	public float VerticalRecoil { get; init; }
	public float HorizontalRecoil { get; init; }
	/// <summary> Movement speeds with the gun out, units per second (PlayerPawn.GetWishSpeed). </summary>
	public float WalkSpeedUnits { get; init; }
	public float SprintSpeedUnits { get; init; }
	public float CrouchSpeedUnits { get; init; }
	public float ProneSpeedUnits { get; init; }
	/// <summary> The gun's loaded weight with its parts, kg (<see cref="Equipment.LoadedMass"/>); 0 if not known. </summary>
	public float Mass { get; init; }

	/// <summary> Up to three words on the gun's character, "|"-separated so the record still compares by value. </summary>
	public string Tags { get; init; } = "";

	public IEnumerable<string> TagList => Tags.Split( '|', StringSplitOptions.RemoveEmptyEntries );

	/// <summary>
	/// The stats of <paramref name="resource"/>: as built in the active class, or with <paramref name="build"/> false,
	/// as it comes from the factory (no parts, no tuning), which the bars show the build's changes against.
	/// </summary>
	public static GunsmithStats Compute( EquipmentResource resource, bool build = true )
	{
		var prefab = resource.IsValid() ? resource.MainPrefab : null;
		var shootable = prefab.IsValid() ? prefab.GetComponentInChildren<Shootable>( true ) : null;
		if ( !shootable.IsValid() )
			return new GunsmithStats();

		var parts = GunsmithAttachmentEffects.ForBuild( build ? resource : null );
		var tune = build ? WeaponTuningManager.GetTuning( resource.ResourceName ) : new WeaponTuningManager.WeaponTuning();
		var suppressed = shootable.HasBuiltInSuppressor || (build && HasSuppressor( resource, shootable ));
		var bolt = prefab.GetComponentInChildren<Boltable>( true ).IsValid();

		// Shootable.GetEffectiveDamage: a suppressor changes the report, not the cartridge.
		var pellets = Math.Max( 1, shootable.BulletCount );
		var damage = shootable.BaseDamage * (1f + tune.Damage * 0.025f);
		var shotDamage = damage * pellets;

		// Shootable.GetEffectiveFireRate: an integral suppressor is already part of the prefab's rate.
		var rpm = shootable.FireRate * parts.FireRate;
		if ( suppressed && !shootable.HasBuiltInSuppressor )
			rpm *= shootable.SuppressorRateScale( parts );
		rpm *= 1f + tune.FireRate * 0.012f;

		var viewModel = resource.ViewModelPrefab.IsValid() ? resource.ViewModelPrefab.GetComponentInChildren<ViewModel>( true ) : null;
		var aimTime = (viewModel.IsValid() ? viewModel.AimTime : 0.25f) * parts.AimTime;

		// PlayerPawn.Movement: the gun's SpeedPenalty comes off the walk speed, then its weight (and its parts') slows
		// every gait.
		var equipment = prefab.GetComponentInChildren<Equipment>( true );
		var penalty = equipment.IsValid() ? equipment.SpeedPenalty : 0f;
		var weight = (equipment.IsValid() ? equipment.WeightSlowdown : 0f) + parts.WeightSlowdown;
		var gunMass = equipment.IsValid() ? equipment.LoadedMass : 0f;
		var speedShare = (WalkSpeed - penalty) / WalkSpeed * (1f - weight);

		float? meters = null;
		if ( shootable.MaxRange < NoFalloffRange )
			meters = FullDamageFraction( shootable.BaseDamageFalloff ) * shootable.MaxRange * parts.DamageFalloffDistance * InchesToMeters;

		float DamageAt( float metres )
		{
			var units = metres / InchesToMeters;
			if ( units > shootable.MaxRange )
				return 0f;
			return damage * shootable.BaseDamageFalloff.Evaluate( units / (shootable.MaxRange * parts.DamageFalloffDistance) );
		}

		var recoil = prefab.GetComponentInChildren<ShootRecoil>( true );
		var recoilScale = 1f - tune.Recoil * 0.015f;
		var (kick, climb, sway) = recoil.IsValid() ? MeanKick( recoil, parts.VerticalRecoil * recoilScale, parts.HorizontalRecoil * recoilScale ) : (0f, 0f, 0f);
		var control = (1f - kick / NoControlKick).Clamp( 0f, 1f );

		// WeaponAmmo.GetEffectiveMaxAmmo: a magazine part sets its own capacity, otherwise tuning scales the standard one.
		var ammo = prefab.GetComponentInChildren<WeaponAmmo>( true );
		var rounds = ammo.IsValid() ? Math.Max( 1, (int)(ammo.MaxAmmo * (1f + tune.MagSize * 0.04f)) ) : 0;
		GunsmithPart magazine = null;
		if ( build && GunsmithLoadoutManager.TryGetAttachment( resource, GunsmithPartType.Magazine, out magazine )
			&& magazine.IsValid() && magazine.MagazineCapacity > 0 )
			rounds = magazine.MagazineCapacity;

		// WeaponAmmo.GetMaxReserve: the spare magazines of the gun's basic load, each as big as the fitted one.
		var spareMags = !ammo.IsValid() ? 0 : ammo.SpareMagazines >= 0 ? ammo.SpareMagazines : WeaponAmmo.DefaultSpareMagazines( resource.Category );

		// Reloadable.GetReloadTime: a magazine with its own reload animations brings its own times, and any magazine
		// part and the tuning scale them (Reloadable.DurationMultiplier).
		var reloadable = prefab.GetComponentInChildren<Reloadable>( true );
		var ownReload = magazine.IsValid() && magazine.ReloadAnimation > 0 ? magazine : null;
		var reloadScale = (magazine.IsValid() ? magazine.ReloadTimeMultiplier.Clamp( 0.5f, 2f ) : 1f) * (1f - tune.Reload * 0.015f);
		var reloadTime = ownReload?.ReloadTime > 0 ? ownReload.ReloadTime : reloadable.IsValid() ? reloadable.ReloadTime : 0f;
		var emptyReloadTime = ownReload?.EmptyReloadTime > 0 ? ownReload.EmptyReloadTime : reloadable.IsValid() ? reloadable.EmptyReloadTime : 0f;

		var tags = new List<string>();
		if ( suppressed ) tags.Add( "SUPPRESSED" );
		if ( bolt ) tags.Add( "BOLT-ACTION" );
		else if ( pellets > 1 ) tags.Add( "BUCKSHOT" );
		if ( shotDamage >= 25f ) tags.Add( "HIGH DAMAGE" );
		if ( rounds >= 45 ) tags.Add( "HIGH CAPACITY" );
		if ( rpm >= 750f ) tags.Add( "HIGH FIRE RATE" );
		if ( control >= 0.65f ) tags.Add( "LOW RECOIL" );
		else if ( control < 0.3f ) tags.Add( "HEAVY RECOIL" );
		if ( meters is { } range ) tags.Add( range < 60f ? "CLOSE RANGE" : range < 100f ? "MID RANGE" : "LONG RANGE" );
		if ( speedShare >= 0.88f ) tags.Add( "MOBILE" );

		return new GunsmithStats
		{
			IsFirearm = true,
			Damage = (shotDamage / 50f).Clamp( 0f, 1f ),
			DamageText = pellets > 1 ? $"{damage:0.#} ×{pellets}" : $"{shotDamage:0.#}",
			FireRate = (rpm / 1000f).Clamp( 0f, 1f ),
			FireRateText = $"{rpm:0} RPM",
			Handling = ((0.5f - aimTime) / 0.35f).Clamp( 0f, 1f ),
			HandlingText = $"{aimTime * 1000f:0} MS",
			Mobility = ((speedShare - 0.7f) / 0.25f).Clamp( 0f, 1f ),
			MobilityText = $"{speedShare * 100f:0}%",
			Range = meters is { } m ? (m / 150f).Clamp( 0f, 1f ) : 1f,
			RangeText = meters is { } shown ? $"{shown:0} M" : "NO FALLOFF",
			Control = control,
			ControlText = $"{control * 100f:0}",
			Rounds = rounds,
			FireModeText = bolt ? "BOLT-ACTION" : FireModes( build ? BuildFireModes( resource, shootable ) : shootable.SupportedFireModes ),
			Tags = string.Join( "|", tags.Take( 3 ) ),
			BulletDamage = damage,
			Pellets = pellets,
			Rpm = rpm,
			AimTime = aimTime,
			ReloadTime = reloadTime * reloadScale,
			EmptyReloadTime = emptyReloadTime * reloadScale,
			SingleReload = reloadable.IsValid() && reloadable.SingleReload,
			Reserve = spareMags * rounds,
			FullDamageRange = meters,
			RangeDamage = (DamageAt( 10f ), DamageAt( 25f ), DamageAt( 50f ), DamageAt( 100f ), DamageAt( 200f )),
			VerticalRecoil = climb / NoControlKick,
			HorizontalRecoil = sway / NoControlKick,
			MuzzleVelocity = shootable.MuzzleVelocity,
			WalkSpeedUnits = (WalkSpeed - penalty) * (1f - weight),
			SprintSpeedUnits = (SprintSpeed - penalty * 0.5f) * (1f - weight),
			CrouchSpeedUnits = CrouchSpeed * (1f - weight),
			ProneSpeedUnits = ProneSpeed * (1f - weight),
			Mass = gunMass > 0f && build ? parts.LoadedMass : gunMass,
		};
	}

	/// <summary> Shootable.UseSuppressedEffects, for the saved build rather than a spawned gun. </summary>
	/// <summary> Equipment.TriggerFireModes: a fitted fire control group's selector, else the weapon's own. </summary>
	private static IReadOnlyList<FireMode> BuildFireModes( EquipmentResource resource, Shootable shootable ) =>
		GunsmithLoadoutManager.TryGetAttachment( resource, GunsmithPartType.Trigger, out var trigger ) && trigger.IsValid()
			&& trigger.FireModes is { Count: > 0 } ? trigger.FireModes : shootable.SupportedFireModes;

	private static bool HasSuppressor( EquipmentResource resource, Shootable shootable )
	{
		if ( GunsmithLoadoutManager.TryGetAttachment( resource, GunsmithPartType.Muzzle, out var muzzle ) && muzzle.IsValid() && muzzle.IsSuppressor )
			return true;
		if ( GunsmithLoadoutManager.TryGetAttachment( resource, GunsmithPartType.Barrel, out var barrel ) && barrel.IsValid()
			&& (barrel.IsSuppressor || (barrel.Name?.Contains( "suppressor", StringComparison.OrdinalIgnoreCase ) ?? false)) )
			return true;
		return shootable.SuppressedAttachment.IsValid() && GunsmithLoadoutManager.HasAttachment( resource, shootable.SuppressedAttachment );
	}

	/// <summary> How far along the falloff curve (0-1 of MaxRange) a hit still does 80% of its damage. </summary>
	private static float FullDamageFraction( Curve falloff )
	{
		const int steps = 400;
		for ( var i = 1; i <= steps; i++ )
		{
			var t = i / (float)steps;
			if ( falloff.Evaluate( t ) < 0.8f )
				return (i - 1) / (float)steps;
		}
		return 1f;
	}

	/// <summary>
	/// The mean kick of one shot, in ShootRecoil's units, with its mean size up and to the side: along the recoil pattern
	/// (whose points ShootRecoil reads with y flipped), or from the middle of the random kick for guns without one.
	/// </summary>
	private static (float Kick, float Up, float Side) MeanKick( ShootRecoil recoil, float vertical, float horizontal )
	{
		var pattern = recoil.RecoilPattern;
		if ( recoil.UseRecoilPattern && pattern.Points is { Count: > 0 } points )
		{
			var total = 0f;
			var totalUp = 0f;
			var totalSide = 0f;
			foreach ( var point in points )
			{
				var up = (RecoilPattern.RangeY.y - point.y) * recoil.Scale.y * vertical;
				var side = point.x * recoil.Scale.x * horizontal;
				total += MathF.Sqrt( up * up + side * side );
				totalUp += MathF.Abs( up );
				totalSide += MathF.Abs( side );
			}
			return (total / points.Count, totalUp / points.Count, totalSide / points.Count);
		}

		var climb = Mean( recoil.VerticalSpread ) * vertical;
		var sway = MeanAbs( recoil.HorizontalSpread ) * horizontal;
		return (MathF.Sqrt( climb * climb + sway * sway ), MathF.Abs( climb ), sway);
	}

	private static (float Min, float Max) Bounds( RangedFloat range ) =>
		range.Range.ToString() == "Fixed" ? (range.FixedValue, range.FixedValue) : (MathF.Min( range.Min, range.Max ), MathF.Max( range.Min, range.Max ));

	private static float Mean( RangedFloat range )
	{
		var (min, max) = Bounds( range );
		return (min + max) * 0.5f;
	}

	/// <summary> The mean size of a value drawn evenly from the range, which may span zero (a kick either way). </summary>
	private static float MeanAbs( RangedFloat range )
	{
		var (min, max) = Bounds( range );
		if ( min >= 0f || max <= 0f || max - min < 0.0001f )
			return MathF.Abs( min + max ) * 0.5f;
		return (min * min + max * max) / (2f * (max - min));
	}

	private static string FireModes( IReadOnlyList<FireMode> modes )
	{
		if ( modes is null || modes.Count == 0 )
			return "SEMI-AUTO";

		var ordered = modes.Distinct().OrderBy( x => x switch { FireMode.Automatic => 0, FireMode.Burst => 1, _ => 2 } ).ToList();
		if ( ordered.Count == 1 )
		{
			return ordered[0] switch
			{
				FireMode.Automatic => "FULL-AUTO",
				FireMode.Burst => "BURST",
				_ => "SEMI-AUTO",
			};
		}

		return string.Join( " / ", ordered.Select( x => x switch
		{
			FireMode.Automatic => "AUTO",
			FireMode.Burst => "BURST",
			_ => "SEMI",
		} ) );
	}
}
