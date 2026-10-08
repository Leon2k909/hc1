namespace Facepunch;

/// <summary>
/// Puddles round one machine's camera while it rains (<see cref="RainView"/>), filling and draining with the rain.
/// Nothing here is networked: every machine finds the same puddles in the same places, since where one lies, how big
/// and deep its hollow is and how much ground drains into it come from the weather's seed and the place, and how full
/// it is from the rain's history (<see cref="Weather.Schedule"/>), which every machine works out the same.
/// <para>
/// Where: the map is cut into 220-unit cells, and each one has a chance of a hollow at a place in it: on level paving
/// (concrete, stone, tile, "default") or on bare earth and gravel, open to the sky, with the ground round it level and
/// the same. Grass, wood, metal and water have none.
/// </para>
/// <para>
/// How full (Tools/puddle_textures.py has the hollows' shapes): a hollow of depth Hd fills from what runs off the
/// ground round it (k times its own area) and the rain on its water, and loses water to seepage and evaporation from its
/// water. Its water surface grows with the depth (a bowl's), so with g the share of its volume that's full,
/// dg/dt = 2 (k Rrun + sqrt(g) (R - s)) / Hd, and the share of its depth that's water is sqrt(g). The runoff Rrun is
/// the rain less what wets the ground first: paving holds the first half millimetre (and dries at 0.05-0.3 mm/h), then
/// sheds 85% of the rest; bare earth soaks rain up at 8 mm/h when dry, slowing to 1 mm/h as its top 3 mm wet through
/// (Horton), and sheds only what comes faster than that. So drizzle puddles paving over hours and never bare earth,
/// steady rain fills paving's in a quarter of an hour, and a shower puddles both within minutes. A puddle drains over
/// hours once it's stopped: seepage through paving's joints at 0.5 mm/h, into earth at 1.5.
/// </para>
/// </summary>
public sealed class RainPuddles
{
	/// <summary> A forced fill for every puddle (0-1, the share of its depth), or below 0 for the rain's (dev_puddles). </summary>
	public static float ForcedFill { get; set; } = -1f;

	private const float Cell = 220f;
	/// <summary> Puddles are found out to this far, and fade out over the last 300. </summary>
	private const float Range = 1700f;
	private const float FadeFrom = 1400f;
	private const float EvictRange = 2000f;
	private const int MaxPuddles = 192;
	private const int ProbesPerFrame = 6;

	/// <summary> The rain's history goes back two hours before the match, in 10 s steps. </summary>
	private const float HistoryStart = -7200f;
	private const float Step = 10f;

	private const string DecalPath = "decals/weather/puddle_{0}_{1}.decal";
	private const int Shapes = 3;

	private enum Ground { Paving, Mud }

	/// <summary> A puddle's hollow, and how full it is at the end of the last whole step of history. </summary>
	private sealed class Site
	{
		public Vector3 Position;
		public Ground Ground;
		public float DepthMm;
		public float Catchment;
		public float Volume;
		public int Steps;
		public GameObject Object;
		public Decal Decal;
		public RealTimeSince SinceShown;
		public bool Shown;
	}

	private readonly Dictionary<(int X, int Y), Site> _cells = new();
	private readonly List<Site> _sites = new();
	private static readonly (int X, int Y)[] Spiral = BuildSpiral();
	private int _next;
	private GameObject _root;
	private RealTimeSince _sinceEvict;

	// The rain's history: each step's rate and runoff off paving and off earth (mm/s), and the ground's stores now.
	private readonly List<float> _rate = new();
	private readonly List<float> _paveRunoff = new();
	private readonly List<float> _mudRunoff = new();
	private float _paveStore, _mudStore;
	private WeatherKind _kind;
	private int _seed;

	private static (int X, int Y)[] BuildSpiral()
	{
		var reach = (int)MathF.Ceiling( Range / Cell );
		var cells = new List<(int X, int Y)>();
		for ( var y = -reach; y <= reach; y++ )
			for ( var x = -reach; x <= reach; x++ )
				if ( MathF.Sqrt( x * x + y * y ) * Cell <= Range + Cell ) cells.Add( (x, y) );
		return cells.OrderBy( c => c.X * c.X + c.Y * c.Y ).ToArray();
	}

	public void Update( Scene scene, Weather weather, RainView.ShelterGrid grid, Vector3 eye, float look )
	{
		if ( !weather.IsValid() ) return;
		if ( weather.Kind != _kind || weather.Seed != _seed ) Reset( weather );

		var now = (float)weather.Elapsed;
		Advance( weather, now );

		if ( !_root.IsValid() )
		{
			// Not under the rain's object, which follows the camera about.
			_root = new GameObject( scene, true, "Rain Puddles" );
			_root.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			_root.NetworkMode = NetworkMode.Never;
		}

		Find( scene, grid, eye );
		if ( _sinceEvict > 0.5f )
		{
			_sinceEvict = 0f;
			Evict( eye );
		}

		Show( weather, eye, now, look );
	}

	public void Dispose()
	{
		if ( _root.IsValid() ) _root.Destroy();
		_root = null;
		_cells.Clear();
		_sites.Clear();
	}

	private void Reset( Weather weather )
	{
		Dispose();
		_kind = weather.Kind;
		_seed = weather.Seed;
		_rate.Clear();
		_paveRunoff.Clear();
		_mudRunoff.Clear();
		_paveStore = 0f;
		_mudStore = 0f;
		_next = 0;
	}

	// ── The rain's history ──────────────────────────────────────────────────────

	/// <summary> The rate (mm/h) over a step: the schedule's before the match, and once it's on, a dev rate if one is set. </summary>
	private static float RateOver( Weather weather, float start )
	{
		var mid = start + Step * 0.5f;
		if ( mid >= 0f && weather.ForcedRate >= 0f ) return weather.ForcedRate;
		return Weather.Schedule.RateAt( weather.Kind, weather.Seed, mid );
	}

	/// <summary> Appends the history's whole steps up to now, and moves every puddle on through them. </summary>
	private void Advance( Weather weather, float now )
	{
		var whole = (int)MathF.Floor( (now - HistoryStart) / Step );
		while ( _rate.Count < whole )
		{
			var rate = RateOver( weather, HistoryStart + _rate.Count * Step );
			var (pave, mud) = Runoff( ref _paveStore, ref _mudStore, rate, Step );
			_rate.Add( rate / 3600f );
			_paveRunoff.Add( pave );
			_mudRunoff.Add( mud );
		}

		foreach ( var site in _sites )
			CatchUp( site );
	}

	/// <summary>
	/// What runs off paving and bare earth (mm/s) over <paramref name="dt"/> seconds of rain at <paramref name="rate"/>
	/// mm/h, and how their stores change.
	/// </summary>
	private static (float Paving, float Mud) Runoff( ref float pave, ref float mud, float rate, float dt )
	{
		var r = rate / 3600f;

		// Paving: a film of half a millimetre wets first, evaporating at 0.3 mm/h once the rain's off (0.05 under it).
		const float paveCap = 0.5f;
		var evaporation = (0.05f + 0.25f * MathF.Exp( -rate / 0.3f )) / 3600f;
		pave += (r - evaporation) * dt;
		var paving = 0f;
		if ( pave > paveCap )
		{
			paving = 0.85f * (pave - paveCap) / dt;
			pave = paveCap;
		}
		pave = MathF.Max( pave, 0f );

		// Bare earth: Horton's infiltration, 8 mm/h into dry ground falling to 1 mm/h as its top 3 mm wet through.
		const float soilCap = 3f, dryRate = 8f / 3600f, wetRate = 1f / 3600f;
		var wet = Math.Clamp( mud / soilCap, 0f, 1f );
		var capacity = wetRate + (dryRate - wetRate) * (1f - wet);
		var soaked = MathF.Min( r, capacity );
		mud = Math.Clamp( mud + (soaked - wetRate * wet) * dt, 0f, soilCap );
		var muddy = MathF.Max( 0f, r - capacity );

		return (paving, muddy);
	}

	/// <summary> A hollow's change in fill (share of its volume) over dt seconds. </summary>
	private static float Fill( Site site, float volume, float rate, float runoff, float dt )
	{
		var seep = (site.Ground == Ground.Paving ? 0.5f : 1.5f) / 3600f;
		var change = 2f * (site.Catchment * runoff + MathF.Sqrt( MathF.Max( volume, 0f ) ) * (rate - seep)) / site.DepthMm;
		return Math.Clamp( volume + change * dt, 0f, 1f );
	}

	private void CatchUp( Site site )
	{
		var runoff = site.Ground == Ground.Paving ? _paveRunoff : _mudRunoff;
		for ( ; site.Steps < _rate.Count; site.Steps++ )
		{
			// Two half steps: a shallow puddle's fill changes fast for the first few millimetres.
			site.Volume = Fill( site, site.Volume, _rate[site.Steps], runoff[site.Steps], Step * 0.5f );
			site.Volume = Fill( site, site.Volume, _rate[site.Steps], runoff[site.Steps], Step * 0.5f );
		}
	}

	/// <summary> A puddle's fill now (share of its depth), the step under way taken at the rain's rate now. </summary>
	private float DepthShare( Site site, Weather weather, float now )
	{
		if ( ForcedFill >= 0f ) return Math.Clamp( ForcedFill, 0f, 1f );

		var into = now - (HistoryStart + site.Steps * Step);
		var volume = site.Volume;
		if ( into > 0f )
		{
			var pave = _paveStore;
			var mud = _mudStore;
			var rate = weather.RainRate;
			var (paving, muddy) = Runoff( ref pave, ref mud, rate, into );
			volume = Fill( site, volume, rate / 3600f, site.Ground == Ground.Paving ? paving : muddy, into );
		}
		return MathF.Sqrt( volume );
	}

	// ── Finding them ────────────────────────────────────────────────────────────

	private void Find( Scene scene, RainView.ShelterGrid grid, Vector3 eye )
	{
		var ox = (int)MathF.Floor( eye.x / Cell );
		var oy = (int)MathF.Floor( eye.y / Cell );
		var probes = 0;
		for ( var n = 0; n < Spiral.Length && probes < ProbesPerFrame; n++ )
		{
			var (sx, sy) = Spiral[n];
			var key = (ox + sx, oy + sy);
			if ( _cells.ContainsKey( key ) ) continue;
			probes++;
			var site = _sites.Count < MaxPuddles ? Probe( scene, grid, key.Item1, key.Item2, eye ) : null;
			_cells[key] = site;
			if ( site is null ) continue;
			_sites.Add( site );
			CatchUp( site );
		}
	}

	private Site Probe( Scene scene, RainView.ShelterGrid grid, int cx, int cy, Vector3 eye )
	{
		var chance = Hash01( cx, cy, 1 );
		// Most cells have no hollow: one cell in four on paving, nearly one in two on a rutted earth track.
		if ( chance >= 0.45f ) return null;

		var at = new Vector3( (cx + 0.5f + 0.7f * (Hash01( cx, cy, 2 ) - 0.5f)) * Cell,
			(cy + 0.5f + 0.7f * (Hash01( cx, cy, 3 ) - 0.5f)) * Cell, 0f );
		var top = eye.z + 600f;
		var down = Down( scene, at.WithZ( top ), top - 4000f );
		if ( !down.Hit || down.StartedSolid || down.Normal.z < 0.985f ) return null;
		if ( down.GameObject is { } hitObject && hitObject.Tags.Has( "water" ) ) return null;
		if ( down.Body is { } body && body.MotionEnabled ) return null;

		var ground = GroundOf( down );
		if ( ground is not { } kind ) return null;
		if ( kind == Ground.Paving && chance >= 0.25f ) return null;

		// Open to the sky over it.
		var up = scene.Trace.Ray( down.HitPosition + Vector3.Up * 2f, down.HitPosition + Vector3.Up * 32000f )
			.WithoutTags( RainView.ShelterGrid.Ignore ).Run();
		if ( up.StartedSolid || (up.Hit && !grid.IsSkyCeiling( up, down.HitPosition.z )) ) return null;

		var u = Hash01( cx, cy, 4 );
		var diameter = kind == Ground.Paving ? MathX.Lerp( 20f, 140f, u * u ) : MathX.Lerp( 40f, 180f, u * u );

		// The ground round it level, and the same ground, out to most of its width.
		var low = down.HitPosition.z;
		var high = low;
		for ( var i = 0; i < 8; i++ )
		{
			var angle = i * MathF.Tau / 8f;
			var ring = down.HitPosition + new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f ) * diameter * 0.4f;
			var tr = Down( scene, ring + Vector3.Up * 24f, ring.z - 24f );
			if ( !tr.Hit || tr.StartedSolid || tr.Normal.z < 0.95f ) return null;
			var dz = tr.HitPosition.z - down.HitPosition.z;
			if ( dz < -2f || dz > 4f || GroundOf( tr ) != kind ) return null;
			low = MathF.Min( low, tr.HitPosition.z );
			high = MathF.Max( high, tr.HitPosition.z );
		}

		var depth = Hash01( cx, cy, 5 );
		var catchment = Hash01( cx, cy, 6 );
		return new Site
		{
			Position = down.HitPosition.WithZ( (low + high) * 0.5f ),
			Ground = kind,
			// Bigger hollows are deeper: a few millimetres in a paving slab's dip, up to 6 cm in a rut.
			DepthMm = kind == Ground.Paving ? MathX.Lerp( 5f, 25f, 0.6f * u + 0.4f * depth ) : MathX.Lerp( 10f, 60f, 0.6f * u + 0.4f * depth ),
			Catchment = kind == Ground.Paving ? MathX.Lerp( 3f, 12f, catchment ) : MathX.Lerp( 4f, 15f, catchment ),
			Object = MakeDecal( kind, (int)(Hash01( cx, cy, 7 ) * Shapes) % Shapes, Hash01( cx, cy, 8 ) * 360f,
				down.HitPosition.WithZ( (low + high) * 0.5f ), diameter, high - low ),
		};
	}

	private static SceneTraceResult Down( Scene scene, Vector3 from, float toZ ) =>
		scene.Trace.Ray( from, from.WithZ( toZ ) ).WithoutTags( Solid ).Run();

	/// <summary> The shelter grid's ignores, less water, which a puddle mustn't lie on. </summary>
	private static readonly string[] Solid = RainView.ShelterGrid.Ignore.Where( t => t != "water" ).ToArray();

	private static Ground? GroundOf( in SceneTraceResult tr )
	{
		var surface = WorldSounds.SurfaceAt( tr );
		if ( (surface?.ResourceName ?? "").Contains( "mud", StringComparison.OrdinalIgnoreCase ) ) return Ground.Mud;
		return WorldSounds.Classify( surface ) switch
		{
			WorldSounds.Material.Masonry or WorldSounds.Material.Tile => Ground.Paving,
			WorldSounds.Material.Dirt => Ground.Mud,
			_ => null,
		};
	}

	private GameObject MakeDecal( Ground ground, int shape, float roll, Vector3 position, float diameter, float relief )
	{
		var definition = ResourceLibrary.Get<DecalDefinition>(
			string.Format( DecalPath, ground == Ground.Paving ? "paving" : "mud", shape ) );
		if ( definition is null || !_root.IsValid() ) return null;

		var go = new GameObject( _root, false, "Puddle" );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.WorldPosition = position;
		go.WorldRotation = Rotation.LookAt( Vector3.Down );

		var decal = go.AddComponent<Decal>();
		decal.Decals = new List<DecalDefinition> { definition };
		var size = diameter / MathF.Max( definition.Width, 1f );
		decal.Size = new Vector2( size, size );
		decal.Rotation = roll;
		// Only as deep as the ground's unevenness, so it hardly paints the boots of whoever stands in it.
		decal.Depth = relief + 10f;
		decal.Parallax = 0f;
		decal.CoverageRange = 0.1f;
		decal.CoverageAmount = 0f;
		decal.ColorTint = Color.White.WithAlpha( 0f );
		return go;
	}

	// ── Showing them ────────────────────────────────────────────────────────────

	private void Show( Weather weather, Vector3 eye, float now, float look )
	{
		foreach ( var site in _sites )
		{
			if ( !site.Object.IsValid() ) continue;
			site.Decal ??= site.Object.Components.Get<Decal>( FindMode.EverythingInSelf );
			if ( site.Decal is null ) continue;

			var fill = DepthShare( site, weather, now );
			var distance = (site.Position - eye).WithZ( 0f ).Length;
			var visible = fill >= 0.01f && distance < Range;
			if ( visible != site.Object.Enabled )
			{
				site.Object.Enabled = visible;
				if ( visible && !site.Shown )
				{
					site.Shown = true;
					site.SinceShown = 0f;
				}
			}
			if ( !visible ) continue;

			var fadeIn = site.Shown ? Math.Clamp( site.SinceShown / 1.5f, 0f, 1f ) : 1f;
			var far = 1f - RainView.SmoothStep( FadeFrom, Range, distance );
			site.Decal.CoverageAmount = MathF.Min( fill, 0.97f );
			site.Decal.ColorTint = Color.White.WithAlpha( fadeIn * far * look );
		}
	}

	private void Evict( Vector3 eye )
	{
		var ox = eye.x / Cell;
		var oy = eye.y / Cell;
		var reach = EvictRange / Cell;
		List<(int X, int Y)> gone = null;
		foreach ( var (key, site) in _cells )
		{
			var dx = key.X + 0.5f - ox;
			var dy = key.Y + 0.5f - oy;
			if ( dx * dx + dy * dy <= reach * reach ) continue;
			(gone ??= new()).Add( key );
			if ( site is null ) continue;
			if ( site.Object.IsValid() ) site.Object.Destroy();
			_sites.Remove( site );
		}

		if ( gone is null ) return;
		foreach ( var key in gone ) _cells.Remove( key );
	}

	/// <summary> A number 0-1 for a cell and a salt, the same on every machine for the match's seed. </summary>
	private float Hash01( int cx, int cy, int salt )
	{
		var h = (uint)cx * 0x8DA6B343u ^ (uint)cy * 0xD8163841u ^ (uint)_seed * 0xCB1AB31Fu ^ (uint)salt * 0x9E3779B1u;
		h ^= h >> 15;
		h *= 0x2C1B3C6Du;
		h ^= h >> 12;
		h *= 0x297A2D39u;
		h ^= h >> 15;
		return (h & 0xFFFFFF) / 16777216f;
	}
}
