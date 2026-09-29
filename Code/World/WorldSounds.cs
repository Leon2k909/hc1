namespace Facepunch;

/// <summary>
/// The world's sounds by what's struck or stood on, in place of s&amp;box's stock ones: a bullet's impact, a boot's step
/// and run, and a landing (sounds/world, made by Tools/world_sounds.py from the physics of each). A surface is sorted
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
	public static SoundEvent BulletImpact( in SceneTraceResult tr, Surface surface )
	{
		if ( tr.Hitbox is not null || (tr.GameObject.IsValid() && tr.GameObject.GetComponentInParent<ZombieAI>().IsValid()) )
		{
			if ( tr.GameObject.IsValid() && tr.GameObject.Root.GetComponentInChildren<PlayerPawn>().IsValid() )
				return null;

			return Event( "sounds/world/impacts/bullet_flesh.sound" ) ?? surface?.SoundCollection.Bullet;
		}

		if ( tr.Collider is Terrain || tr.GameObject?.Components.Get<Terrain>() is not null )
			surface = SurfaceAt( tr );

		var material = Classify( surface );
		var ours = material is Material.Own ? null : Event( $"sounds/world/impacts/bullet_{Name( material )}.sound" );
		return ours ?? surface?.SoundCollection.Bullet ?? surface?.GetBaseSurface()?.SoundCollection.Bullet;
	}

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
