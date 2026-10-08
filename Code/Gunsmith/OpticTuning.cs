namespace Facepunch.Gunsmith;

/// <summary>
/// Optic tuning, after Modern Warfare II's (2022): two sliders on the fitted optic, saved with the build. Each one is what
/// a shooter really sets up on a sight:
/// <list type="bullet">
/// <item>Eye Position slides the optic along its rail, one Picatinny slot at a time. Closer, its window or eyepiece
/// fills more of the view; further, less, with more of the world round it. A magnified optic also has an eye relief, so
/// off its rated relief the picture shrinks and shades (<see cref="ScopeEyeBox"/>).</item>
/// <item>Zero is the elevation turret: the range where the bullet's path comes back down through the line of sight
/// (<see cref="Shootable.ZeroRange"/>). It only moves the shots where bullets drop (Battle Royale's
/// <see cref="BulletDrop"/>).</item>
/// </list>
/// Only the MWII optics on the M4's mounts (<see cref="GunsmithMw22Attachment"/>) take it: their rail shift is a plain
/// slide along the bore, which leaves the sight line where it was.
/// </summary>
public static class OpticTuning
{
	/// <summary>MIL-STD-1913's slot spacing: 0.394 in.</summary>
	public const float SlotPitch = 0.394f;

	/// <summary>How far in front of the eye the M4 holds an optic's origin before its OpticAimOffset (Tools/optic_eyepieces.py).</summary>
	public const float OpticDepth = 8.718f;

	/// <summary>
	/// The most elevation a zero may need above the bore's line, in radians: 12 mrad (about 40 MOA), what common red dots'
	/// and holographic sights' turrets give (an Aimpoint's ±1 m at 100 m, an EOTech's 40 MOA).
	/// </summary>
	public const float MaxElevation = 0.012f;

	/// <summary>Zeros a turret is set to, in metres. The gun's own zero is offered too.</summary>
	public static readonly int[] Zeros = { 25, 50, 100, 150, 200, 250, 300, 400, 500, 600 };

	/// <summary>
	/// How many slots each weapon's optic can move back (towards the eye) and forward from where it's mounted, kept on
	/// its rail and clear of what's behind it. Not yet checked on every gun in-game.
	/// </summary>
	private static readonly Dictionary<string, (int Back, int Forward)> Travel = new( StringComparer.OrdinalIgnoreCase )
	{
		// Flat-top receivers with the handguard's top rail running on in front.
		["m4a1"] = (2, 2),
		["m16"] = (2, 2),
		["aug"] = (2, 2),
		// The MCX's top rail runs the whole length of the upper and handguard.
		["mcx"] = (2, 3),
		// The optic sits at the back of a top rail that ends behind it.
		["p90"] = (0, 2),
		["mp7"] = (0, 2),
		// The claw mount is a short rail with the optic at its back.
		["uzi"] = (0, 1),
		// Short rails: the AKs' and Vepr's, the FAL's top cover and the FAMAS's.
		["kastov762"] = (1, 1),
		["kastov74u"] = (1, 1),
		["vityaz"] = (1, 1),
		["rpk"] = (1, 1),
		["bizon"] = (1, 1),
		["ak105"] = (1, 1),
		["vepr12"] = (1, 1),
		["fal"] = (1, 1),
		["famas"] = (1, 1),
	};

	public static bool IsTunable( GunsmithPart part ) =>
		part.IsValid() && part.Category == GunsmithPartType.Optic && part.OverrideAimOffset
		&& (part.ResourcePath ?? "").StartsWith( "gunsmith/m4a1/mw2022/", StringComparison.OrdinalIgnoreCase );

	/// <summary>Slots the optic can move back (towards the eye) and forward on this weapon.</summary>
	public static (int Back, int Forward) RailTravel( EquipmentResource resource ) =>
		resource.IsValid() && Travel.TryGetValue( resource.ResourceName ?? "", out var travel ) ? travel : (1, 1);

	public static int ClampSlots( EquipmentResource resource, int slots )
	{
		var travel = RailTravel( resource );
		return Math.Clamp( slots, -travel.Back, travel.Forward );
	}

	/// <summary>The optic's slide along the bore for <paramref name="slots"/>, in inches (forward is positive).</summary>
	public static float RailShift( int slots ) => slots * SlotPitch;

	/// <summary>How far in front of the eye the optic's origin sits at its rated place.</summary>
	public static float OriginDistance( GunsmithPart optic ) => OpticDepth + optic.OpticAimOffset.x;

	/// <summary>The rated eye relief to a magnified optic's eyepiece glass (Tools/optic_eyepieces.py), or 0 with none known.</summary>
	public static float RatedEyeRelief( GunsmithPart optic ) =>
		optic.IsValid() && optic.OpticEyepieceDiameter > 0f ? OpticDepth + optic.OpticAimOffset.x + optic.OpticEyepiece.x : 0f;

	/// <summary>The gun's shooting component as its prefab has it, for its ballistics.</summary>
	public static Shootable FactoryShootable( EquipmentResource resource )
	{
		var prefab = resource.IsValid() ? resource.MainPrefab : null;
		return prefab.IsValid() ? prefab.GetComponentInChildren<Shootable>( true ) : null;
	}

	/// <summary>Whether the gun has a real load to zero, with <see cref="Ballistics"/> figures.</summary>
	public static bool HasBallistics( Shootable shootable ) =>
		shootable.IsValid() && shootable.MuzzleVelocity > 0f && shootable.BallisticCoefficient > 0f && shootable.ZeroRange > 0f;

	/// <summary>The bore's angle above the line of sight for a zero, in radians, as <see cref="Shootable"/> works it out.</summary>
	public static float Elevation( Shootable shootable, float zero )
	{
		var path = Ballistics.Get( shootable.DragFunction, shootable.MuzzleVelocity, shootable.BallisticCoefficient );
		return (shootable.SightHeight / Ballistics.UnitsPerMeter + path.DropAt( zero )) / zero;
	}

	/// <summary>Where the bullet passes at a range, in metres above (positive) or below the point of aim, for a zero.</summary>
	public static float HeightAt( Shootable shootable, float zero, float range )
	{
		var path = Ballistics.Get( shootable.DragFunction, shootable.MuzzleVelocity, shootable.BallisticCoefficient );
		return Elevation( shootable, zero ) * range - shootable.SightHeight / Ballistics.UnitsPerMeter - path.DropAt( range );
	}

	/// <summary>
	/// The zeros the optic's turret can reach on this gun, nearest first: <see cref="Zeros"/> up to
	/// <see cref="MaxElevation"/>, plus the gun's own.
	/// </summary>
	public static List<int> ZeroChoices( Shootable shootable )
	{
		if ( !HasBallistics( shootable ) ) return new();
		var factory = (int)MathF.Round( shootable.ZeroRange );
		return Zeros.Where( zero => zero == factory || Elevation( shootable, zero ) <= MaxElevation )
			.Append( factory ).Distinct().OrderBy( zero => zero ).ToList();
	}
}
