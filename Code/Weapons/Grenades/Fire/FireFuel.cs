namespace Facepunch;

/// <summary>
/// What a fire finds to burn on the ground (<see cref="SurfaceFire"/>). Only cured grass carries a running fire; the
/// others burn where they're lit and go out by themselves.
/// </summary>
public enum FireFuel : byte
{
	/// <summary> Nothing that burns: rock, earth, gravel, concrete, metal, glass. </summary>
	None,
	/// <summary> Dead, dry grass: Ridgeback's dry meadow. </summary>
	CuredGrass,
	/// <summary> Green meadow: too much live grass in it to carry a fire, so only a lit patch burns. </summary>
	GreenGrass,
	/// <summary> A mown lawn: a grass surface that isn't terrain, like Flatgrass's. </summary>
	Lawn,
	/// <summary> Timber floors, decks and furniture. </summary>
	Wood,
	/// <summary> Upholstery, carpet, curtains, cardboard. </summary>
	Fabric,
}

/// <summary>
/// How each <see cref="FireFuel"/> burns. Grass follows CSIRO's grassland fire model (Cheney, Gould and Catchpole 1998,
/// natural pasture) for the head fire's speed, the Canadian FBP system's length-to-breadth ratio for the burnt area's
/// shape, McArthur's slope rule (Noble et al. 1980) and Byram's flame length.
/// </summary>
public static class FireFuels
{
	public const float Metre = WorldWind.UnitsPerMetre;

	/// <summary> Grass's heat of combustion, kJ/kg, for Byram's fireline intensity. </summary>
	private const float HeatOfCombustion = 18600f;

	/// <summary>
	/// Curing (% of the grass that's dead), load (kg/m² of it that burns in the flames), dead fuel moisture (%) and the
	/// flames' residence time at any one spot (s). For fuels that don't spread: the flames' height (m) and how long a
	/// lit patch burns (s). SpatterIgnition is the chance a drop of burning iron from thermite lights it.
	/// </summary>
	public readonly record struct Behaviour( float Curing, float Load, float Moisture, float Residence,
		float PatchFlame, float PatchBurn, float SpatterIgnition );

	public static Behaviour Of( FireFuel fuel ) => fuel switch
	{
		// Natural pasture of about 3.5 t/ha, fully cured, on a warm dry afternoon: McArthur's grass moisture at 25 C and
		// 40% humidity is about 9%.
		FireFuel.CuredGrass => new( 95f, 0.35f, 9f, 8f, 0.4f, 20f, 0.4f ),
		// About 40% cured: CSIRO's curing factor is under 0.1 there, below which grass doesn't carry a fire.
		FireFuel.GreenGrass => new( 40f, 0.35f, 9f, 8f, 0.25f, 25f, 0.03f ),
		FireFuel.Lawn => new( 20f, 0.15f, 9f, 6f, 0.15f, 15f, 0.01f ),
		// A drop of molten iron seldom lights solid timber, and a lit floorboard goes out once nothing else heats it.
		FireFuel.Wood => new( 0f, 0f, 12f, 0f, 0.3f, 90f, 0.02f ),
		FireFuel.Fabric => new( 0f, 0f, 8f, 0f, 0.7f, 60f, 0.35f ),
		_ => default,
	};

	/// <summary> CSIRO's curing factor: 1 for dead grass, under 0.1 (no spread) below about 45% cured. </summary>
	public static float CuringFactor( float curing ) => 1.036f / (1f + 103.989f * MathF.Exp( -0.0996f * (curing - 20f) ));

	/// <summary> Does a fire run through it, or only burn where it's lit? </summary>
	public static bool Spreads( FireFuel fuel ) => fuel is FireFuel.CuredGrass or FireFuel.GreenGrass or FireFuel.Lawn
		&& CuringFactor( Of( fuel ).Curing ) >= 0.1f;

	private static float MoistureFactor( float moisture, float windKmh ) => moisture < 12f
		? MathF.Exp( -0.108f * moisture )
		: MathF.Max( 0f, windKmh <= 10f ? 0.684f - 0.0342f * moisture : 0.547f - 0.0228f * moisture );

	/// <summary>
	/// The head fire's rate of spread on level ground (m/s) in a 10 m wind of <paramref name="windKmh"/> km/h, or 0 for a
	/// fuel that doesn't carry a fire.
	/// </summary>
	public static float HeadRate( FireFuel fuel, float windKmh )
	{
		if ( !Spreads( fuel ) ) return 0f;
		var b = Of( fuel );
		var kmh = windKmh < 5f
			? 0.054f + 0.269f * windKmh
			: 1.4f + 0.838f * MathF.Pow( windKmh - 5f, 0.844f );
		// Rain wets the grass (Weather.FuelWetting), and past about 20% moisture a grass fire stops running.
		return kmh * MoistureFactor( b.Moisture + Weather.FuelWetting, windKmh ) * CuringFactor( b.Curing ) / 3.6f;
	}

	/// <summary> The burnt area's length over its breadth (FBP, grass): round in still air, longer the stronger the wind. </summary>
	public static float LengthToBreadth( float windKmh ) => windKmh <= 1f ? 1f : MathF.Max( 1f, 1.1f * MathF.Pow( windKmh, 0.464f ) );

	/// <summary>
	/// The rate of spread (m/s) in a direction whose angle from straight downwind has the cosine
	/// <paramref name="cosFromWind"/>. The fire grows as an ellipse from its rear focus: the head fire downwind, the flanks
	/// at (1-e) of it, and the backing fire upwind at (1-e)/(1+e).
	/// </summary>
	public static float RateAt( float head, float lengthToBreadth, float cosFromWind )
	{
		var e = MathF.Sqrt( MathF.Max( 0f, 1f - 1f / (lengthToBreadth * lengthToBreadth) ) );
		return head * (1f - e) / (1f - e * cosFromWind);
	}

	/// <summary> McArthur: a fire's speed doubles for every 10 degrees it runs uphill and halves for every 10 down. </summary>
	public static float SlopeFactor( float degrees ) => MathF.Exp( 0.069f * Math.Clamp( degrees, -20f, 20f ) );

	/// <summary> Byram's flame length (m) for a front moving through the fuel at <paramref name="rate"/> m/s. </summary>
	public static float FlameLength( FireFuel fuel, float rate )
	{
		var intensity = HeatOfCombustion * Of( fuel ).Load * MathF.Max( rate, 0f ); // kW/m
		return 0.0775f * MathF.Pow( intensity, 0.46f );
	}

	/// <summary>
	/// The fuel where a downward trace hit the ground. Terrain goes by the material painted there; anything else by its
	/// surface and the surfaces it's based on.
	/// </summary>
	public static FireFuel Classify( in SceneTraceResult tr )
	{
		if ( !tr.Hit ) return FireFuel.None;

		var terrain = tr.Collider as Terrain ?? tr.GameObject?.Components.Get<Terrain>();
		if ( terrain.IsValid() )
			return TerrainFuel( terrain.GetMaterialAtWorldPosition( tr.HitPosition )?.GetDominantMaterial() );

		return SurfaceFuel( tr.Surface, false );
	}

	private static FireFuel TerrainFuel( TerrainMaterial material )
	{
		if ( material is null ) return FireFuel.None;
		var name = material.ResourceName ?? "";
		if ( name.Contains( "meadow_dry" ) || name.Contains( "dry_grass" ) || name.Contains( "straw" ) )
			return FireFuel.CuredGrass;
		return SurfaceFuel( material.Surface, true );
	}

	private static FireFuel SurfaceFuel( Surface surface, bool terrain )
	{
		for ( var i = 0; surface is not null && i < 6; i++, surface = surface.GetBaseSurface() )
		{
			var name = surface.ResourceName ?? "";
			if ( name.StartsWith( "grass" ) ) return terrain ? FireFuel.GreenGrass : FireFuel.Lawn;
			if ( name.StartsWith( "wood" ) ) return FireFuel.Wood;
			if ( name.StartsWith( "fabric" ) || name.StartsWith( "cloth" ) || name.StartsWith( "carpet" )
				|| name.StartsWith( "cardboard" ) || name.StartsWith( "paper" ) )
				return FireFuel.Fabric;
		}

		return FireFuel.None;
	}
}
