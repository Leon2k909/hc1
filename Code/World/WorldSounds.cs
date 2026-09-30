namespace Facepunch;

/// <summary>
/// The world's sounds by what's struck or stood on, in place of s&amp;box's stock ones: a bullet's impact, a knife's strike
/// and swing, a grenade's bounce, a boot's step and run, and a landing (sounds/world, made by Tools/world_sounds.py from
/// the physics of each). A surface is sorted
/// into one of the materials the script has sounds for by its name, then its base surfaces' names. Anything else (water,
/// snow, mud, a carpet underfoot) keeps its own surface's sounds, and so does a set whose event hasn't compiled yet.
/// </summary>
public static class WorldSounds
{
	public enum Material
	{
		/// <summary> None of ours: the surface's own sounds. </summary>
		Own,
		Masonry,
		Tile,
		Metal,
		SheetMetal,
		Glass,
		Wood,
		Plastic,
		Dirt,
		Grass,
		Fabric,
		Flesh,
	}

	private static readonly Dictionary<Surface, Material> Materials = new();

	/// <summary>
	/// What a surface is made of, from its name or, failing that, its base surfaces'. "default", which most of a map's
	/// walls and floors are, is masonry.
	/// </summary>
	public static Material Classify( Surface surface )
	{
		if ( surface is null )
			return Material.Own;

		if ( Materials.TryGetValue( surface, out var known ) )
			return known;

		Material? found = null;
		var current = surface;
		for ( var depth = 0; current is not null && depth < 8 && found is null; depth++, current = current.GetBaseSurface() )
			found = ByName( current.ResourceName?.ToLowerInvariant() ?? "" );

		return Materials[surface] = found ?? Material.Own;
	}

	private static Material? ByName( string name )
	{
		if ( name.Length == 0 ) return null;
		if ( Has( name, "water", "slime", "wade", "snow", "ice", "mud" ) ) return Material.Own;
		if ( Has( name, "flesh", "blood", "alien", "zombie" ) ) return Material.Flesh;
		if ( Has( name, "glass" ) ) return Material.Glass;
		if ( Has( name, "metal.sheet", "sheetmetal", "sheet_metal", "tin", "chainlink", "vent", "duct" ) )
			return Material.SheetMetal;
		if ( Has( name, "metal", "steel", "iron", "grate", "grating" ) ) return Material.Metal;
		if ( Has( name, "ceramic", "tile", "porcelain" ) ) return Material.Tile;
		if ( Has( name, "wood", "plank", "parquet", "plywood" ) ) return Material.Wood;
		if ( Has( name, "plastic", "rubber" ) ) return Material.Plastic;
		if ( Has( name, "fabric", "cloth", "carpet", "cardboard", "paper", "sandbag", "foam", "cushion" ) )
			return Material.Fabric;
		if ( Has( name, "grass", "foliage", "leaves", "leaf", "hay", "straw" ) ) return Material.Grass;
		if ( Has( name, "dirt", "soil", "earth", "sand", "gravel" ) ) return Material.Dirt;
		if ( Has( name, "default", "concrete", "brick", "stone", "rock", "plaster", "asphalt", "cement", "masonry",
			"marble", "granite" ) )
			return Material.Masonry;
		return null;
	}

	private static readonly char[] Separators = { '.', '_', '-', ' ', '/' };

	/// <summary>
	/// Whether the name has any of the words. A short word has to start one of the name's parts ("tile" in
	/// "floor_tiles", not "ice" in "office"); a longer one can be anywhere in it.
	/// </summary>
	private static bool Has( string name, params string[] words )
	{
		string[] parts = null;
		foreach ( var word in words )
		{
			if ( word.Length > 4 || word.Contains( '.' ) )
			{
				if ( name.Contains( word ) ) return true;
				continue;
			}

			parts ??= name.Split( Separators, StringSplitOptions.RemoveEmptyEntries );
			foreach ( var part in parts )
				if ( part.StartsWith( word ) ) return true;
		}
		return false;
	}

	/// <summary>
	/// The surface a trace hit. On terrain that's the ground material under the hit (a meadow's grass, a road's dirt),
	/// which the trace's own surface doesn't give.
	/// </summary>
	public static Surface SurfaceAt( in SceneTraceResult tr )
	{
		var terrain = tr.Collider as Terrain ?? tr.GameObject?.Components.Get<Terrain>();
		if ( terrain.IsValid() && terrain.GetMaterialAtWorldPosition( tr.HitPosition )?.GetDominantMaterial() is { } ground
			&& ground.Surface is not null )
			return ground.Surface;

		return tr.Surface;
	}

	/// <summary>
	/// The sound of a bullet striking what <paramref name="tr"/> hit, whose surface is <paramref name="surface"/>, or
	/// null for none. A living player's body has none here: <see cref="PlayerPawn.BloodImpactSound"/> plays it on every
	/// machine. Other bodies (bots, zombies, corpses) sound like flesh whatever their colliders' surfaces are.
	/// </summary>
	public static SoundEvent BulletImpact( in SceneTraceResult tr, Surface surface ) => Strike( tr, surface, "impacts/bullet" );

	/// <summary>
	/// The sound of a knife's blade striking what <paramref name="tr"/> hit, like <see cref="BulletImpact"/>: the steel
	/// tip, the blade's ring and what the tip does to the face, far quieter than a round's strike. A living player's
	/// body plays <see cref="KnifeFlesh"/> on every machine as it takes the stab.
	/// </summary>
	public static SoundEvent KnifeImpact( in SceneTraceResult tr, Surface surface ) => Strike( tr, surface, "knife/knife" );

	/// <summary> A knife's stab into a body, or null until it's compiled. </summary>
	public static SoundEvent KnifeFlesh => Event( "sounds/world/knife/knife_flesh.sound" );

	/// <summary> A knife's blade cutting the air in a swing, or null until it's compiled. </summary>
	public static SoundEvent KnifeSwing => Event( "sounds/world/knife/knife_swing.sound" );

	private static SoundEvent Strike( in SceneTraceResult tr, Surface surface, string set )
	{
		if ( tr.Hitbox is not null || (tr.GameObject.IsValid() && tr.GameObject.GetComponentInParent<ZombieAI>().IsValid()) )
		{
			if ( tr.GameObject.IsValid() && tr.GameObject.Root.GetComponentInChildren<PlayerPawn>().IsValid() )
				return null;

			return Event( $"sounds/world/{set}_flesh.sound" ) ?? surface?.SoundCollection.Bullet;
		}

		if ( tr.Collider is Terrain || tr.GameObject?.Components.Get<Terrain>() is not null )
			surface = SurfaceAt( tr );

		var material = Classify( surface );
		var ours = material is Material.Own ? null : Event( $"sounds/world/{set}_{Name( material )}.sound" );
		return ours ?? surface?.SoundCollection.Bullet ?? surface?.GetBaseSurface()?.SoundCollection.Bullet;
	}

	/// <summary> What a thrown grenade is, for the sound of its bounces. </summary>
	public enum GrenadeBody
	{
		/// <summary> A filled steel sphere, an M67: a dull clunk. </summary>
		Frag,
		/// <summary> A thin sheet-steel can (smoke, stun, thermite): a hollow tonk that rings a little. </summary>
		Can,
	}

	/// <summary> The impact speed, in units a second, at which a bounce plays at its event's own volume (~6 m/s). </summary>
	public const float BounceReferenceSpeed = 240f;

	/// <summary> Slower than this (~1 m/s) a grenade rolls or settles without a knock worth hearing. </summary>
	public const float BounceMinSpeed = 40f;

	/// <summary> Whether the grenade bounces have compiled, so a grenade can turn the engine's own collision sounds off. </summary>
	public static bool HasGrenadeBounces => Event( "sounds/world/grenades/frag_concrete.sound" ) is not null;

	/// <summary>
	/// A grenade of <paramref name="body"/> striking <paramref name="surface"/>, or null where we have none (water, snow,
	/// mud): the caller plays the surface's own. <see cref="BounceVolume"/> scales it by how hard it hit.
	/// </summary>
	public static SoundEvent GrenadeBounce( Surface surface, GrenadeBody body )
	{
		var floor = Classify( surface ) switch
		{
			Material.Masonry => "concrete",
			Material.Tile or Material.Glass => "tile",
			Material.Wood or Material.Plastic => "wood",
			Material.Metal or Material.SheetMetal => "metal",
			Material.Dirt => "dirt",
			Material.Grass => "grass",
			Material.Fabric or Material.Flesh => "soft",
			_ => null,
		};
		return floor is null ? null : Event( $"sounds/world/grenades/{body.ToString().ToLowerInvariant()}_{floor}.sound" );
	}

	/// <summary>
	/// How loud a bounce at <paramref name="speed"/> (into the surface) is against one at
	/// <see cref="BounceReferenceSpeed"/>: an elastic impact's peak force, and so its sound, grows as the speed to the 1.2
	/// (Hertz). 0 under <see cref="BounceMinSpeed"/>, at most 2 (a throw's first landing, ~12 m/s).
	/// </summary>
	public static float BounceVolume( float speed ) =>
		speed < BounceMinSpeed ? 0f : MathF.Min( MathF.Pow( speed / BounceReferenceSpeed, 1.2f ), 2f );

	/// <summary>
	/// A boot on this floor: a walking step or, sprinting, a running one. <paramref name="left"/> picks the surface's own
	/// left or right step where it keeps its own.
	/// </summary>
	public static SoundEvent Footstep( Surface surface, bool running, bool left )
	{
		var floor = Floor( Classify( surface ) );
		var ours = floor is null ? null : Event( $"sounds/world/footsteps/{(running ? "run" : "step")}_{floor}.sound" );
		return ours ?? (left ? surface?.SoundCollection.FootLeft : surface?.SoundCollection.FootRight);
	}

	/// <summary> Both boots coming down on this floor after a jump or a fall, or null for the caller's own. </summary>
	public static SoundEvent Landing( Surface surface )
	{
		var floor = Floor( Classify( surface ) );
		return (floor is null ? null : Event( $"sounds/world/footsteps/land_{floor}.sound" )) ?? surface?.SoundCollection.FootLand;
	}

	/// <summary> The footstep set for a floor: glass underfoot is a glazed tile, sheet metal a deck. </summary>
	private static string Floor( Material material ) => material switch
	{
		Material.Masonry => "concrete",
		Material.Tile or Material.Glass => "tile",
		Material.Wood => "wood",
		Material.Metal or Material.SheetMetal => "metal",
		Material.Dirt => "dirt",
		Material.Grass => "grass",
		_ => null,
	};

	private static string Name( Material material ) => material.ToString().ToLowerInvariant();

	/// <summary> A compiled event, or null until it is. Not cached, so one compiled mid-session is picked up. </summary>
	private static SoundEvent Event( string path ) => ResourceLibrary.Get<SoundEvent>( path );
}
