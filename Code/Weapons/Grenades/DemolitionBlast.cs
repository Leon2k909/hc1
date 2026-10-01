namespace Facepunch;

/// <summary>
/// What a demolition charge going off on the ground looks like to each machine, built in code from the engine's own
/// sheets. Sized from the real thing: the C4's 9 kg charge (Tools/ordnance_sounds.py's figure), about 12 kg of TNT,
/// which on the ground acts like ~22 kg in the open (<see cref="EquivalentKg"/>).
/// <list type="bullet">
/// <item>The detonation's flash and a fireball about 8 m across, white-hot for a tenth of a second, then a dull
/// orange going to black soot as it rolls up (<see cref="FireballParticles"/>).</item>
/// <item>A burst of the ground's own dust thrown up and out, and the base surge: a ring of dust the blast drives along
/// the ground, which stops 10-15 m out and hangs (<see cref="BlastCloudParticles"/>).</item>
/// <item>Chunks of the ground and grit thrown 10-45 m/s on ballistic arcs under real gravity and air drag, which bounce
/// and lie where they land (<see cref="DebrisParticles"/>), and hot sparks.</item>
/// <item>A column of soot and dust 15-25 m tall that drifts with the wind and takes about half a minute to thin
/// out.</item>
/// <item>A light as bright as the fireball, the ground scorched 10 m across, loose physics objects thrown, and the
/// ground shock shaking the view by the blast's overpressure where the viewer is, when it gets to them.</item>
/// </list>
/// Everything is local to each machine (the explosion object is spawned by the host, so this runs everywhere).
/// </summary>
[Title( "Demolition Blast" )]
public sealed class DemolitionBlast : Component
{
	/// <summary> The charge, kg of C4. </summary>
	[Property] public float ChargeKg { get; set; } = 9f;

	/// <summary> C4's TNT equivalence by blast. </summary>
	public const float TntEquivalence = 1.34f;

	/// <summary> A charge on the ground: the ground reflects its blast, so it acts like this much more in the open. </summary>
	public const float SurfaceBurstFactor = 1.8f;

	/// <summary> The TNT in the open with the same blast, kg. </summary>
	public float EquivalentKg => ChargeKg * TntEquivalence * SurfaceBurstFactor;

	/// <summary> Real gravity, 9.81 m/s², in units. The debris flies at life size. </summary>
	public const float Gravity = 9.81f * Ballistics.UnitsPerMeter;

	private const string FireballSheet = "textures/particles/flame/explosion/explosion_01.vtex";
	private const string FlashSheet = "textures/particles/flame/explosion/explosion_03.vtex";
	private const string SoilBurstSheet = "textures/particles/flame/explosion/explosion_02.vtex";
	private const string SurgeSheet = "textures/particles/smoke/smoke_burst_a.vtex";
	private const string PlumeSheet = "textures/particles/smoke/smoke_burst_c.vtex";
	private const string ColumnSheet = "textures/particles/smoke/smoke_loop_c.vtex";
	private const string ChunkSheet = "textures/particles/impact/rock_chunks_01.vtex";
	private const string GritSheet = "textures/particles/particle_debris_02.vtex";
	private const string ScorchDecal = "decals/fire/burnt_patch.decal";

	/// <summary> rock_chunks_01's sheet holds this many chunk shapes, one a sequence. </summary>
	private const int ChunkShapes = 6;

	/// <summary> The column's puffs keep coming up off the ground and out of the fireball for this long. </summary>
	private const float ColumnFeedTime = 3f;
	private const int ColumnPuffs = 36;

	private ParticleEffect _fireball, _flash, _soil, _surge, _plume, _column, _chunks, _grit, _sparks;
	private BlastCloudParticles[] _clouds;
	private PointLight _light;
	private Vector3 _ground;
	private Ground _kind;
	private TimeSince _sinceStart;
	private int _columnEmitted;
	private float _shakeAt = -1f;
	private float _shakeSize;
	private WorldWind _wind;

	private enum Ground { Masonry, Soil, Grass, Wood }

	protected override void OnStart()
	{
		_sinceStart = 0;
		FindGround();

		var root = GameObject;
		_flash = FireParticles.Create<FireballParticles>( root, "Flash", FlashSheet, 4, additive: true, feather: 16f );
		_fireball = FireParticles.Create<FireballParticles>( root, "Fireball", FireballSheet, 16, additive: false, sorted: true, feather: 16f );
		_soil = FireParticles.Create<BlastCloudParticles>( root, "Soil Burst", _kind == Ground.Masonry ? PlumeSheet : SoilBurstSheet, 16, additive: false, sorted: true, feather: 24f );
		_surge = FireParticles.Create<BlastCloudParticles>( root, "Base Surge", SurgeSheet, 32, additive: false, sorted: true, feather: 24f );
		_plume = FireParticles.Create<BlastCloudParticles>( root, "Plume", PlumeSheet, 6, additive: false, sorted: true, feather: 32f );
		_column = FireParticles.Create<BlastCloudParticles>( root, "Column", ColumnSheet, 48, additive: false, sorted: true, feather: 32f );
		_grit = FireParticles.Create<BlastCloudParticles>( root, "Grit", GritSheet, 32, additive: false, feather: 4f );
		_chunks = FireParticles.Create<DebrisParticles>( root, "Debris", ChunkSheet, 96, additive: false, feather: 0f );
		_sparks = FireParticles.Create<SparkParticles>( root, "Sparks", FireParticles.Spark, 80, additive: true, feather: 0f );

		// Chunks and sparks hit the ground and bounce: the chunks hardly, the sparks skip off.
		foreach ( var (effect, bounce, friction, radius) in new[] { (_chunks, 0.25f, 1.2f, 2f), (_sparks, 0.35f, 0.6f, 0.5f) } )
		{
			effect.Collision = true;
			effect.CollisionRadius = radius;
			effect.Bounce = bounce;
			effect.Friction = friction;
			effect.CollisionIgnore = new TagSet( new[] { "trigger", "playerclip", "grenade", "particles", "movement", "player", "ragdoll", "corpse" } );
		}

		_clouds = new[] { _soil, _surge, _plume, _column, _grit }.Select( x => x.GetComponent<BlastCloudParticles>() ).ToArray();

		var sparks = _sparks.GetComponent<ParticleSpriteRenderer>();
		sparks.MotionBlur = true;
		sparks.LeadingTrail = false;
		sparks.BlurAmount = 0.6f;
		sparks.BlurSpacing = 0.5f;
		sparks.BlurOpacity = 0.8f;

		EmitFlashAndFireball();
		EmitDust();
		EmitDebris();
		CreateLight();
		PlaceScorch();
		ThrowLooseObjects();
		ScheduleShake();
	}

	protected override void OnUpdate()
	{
		var t = (float)_sinceStart;
		var wind = SampleWind( _ground + Vector3.Up * 300f );
		foreach ( var cloud in _clouds )
		{
			if ( cloud.IsValid() ) cloud.Wind = wind;
		}
		if ( _sparks.IsValid() && _sparks.GetComponent<SparkParticles>() is { } sparkParticles )
			sparkParticles.Wind = wind;
		if ( _fireball.IsValid() && _fireball.GetComponent<FireballParticles>() is { } fireball )
			fireball.Wind = wind;

		FeedColumn( t );
		UpdateLight( t );

		if ( _shakeAt >= 0f && t >= _shakeAt )
		{
			_shakeAt = -1f;
			// Big and short close in, a long low rumble further out.
			ScreenShaker.Main?.Add( new ScreenShake.Random( 0.5f + 0.12f * _shakeSize, _shakeSize ) );
		}
	}

	/// <summary> Where the ground under the charge is, and what it's made of: the dust and chunks are its own. </summary>
	private void FindGround()
	{
		var origin = WorldPosition;
		var tr = Scene.Trace.Ray( origin + Vector3.Up * 24f, origin + Vector3.Down * 96f )
			.WithoutTags( "trigger", "playerclip", "player", "ragdoll", "corpse", "movement", "particles", "grenade" )
			.IgnoreGameObjectHierarchy( GameObject )
			.Run();
		_ground = tr.Hit ? tr.HitPosition : origin;
		_kind = !tr.Hit ? Ground.Masonry : WorldSounds.Classify( WorldSounds.SurfaceAt( tr ) ) switch
		{
			WorldSounds.Material.Dirt => Ground.Soil,
			WorldSounds.Material.Grass => Ground.Grass,
			WorldSounds.Material.Wood => Ground.Wood,
			_ => Ground.Masonry,
		};
	}

	/// <summary> The colour the ground's dust is, and its chunks. </summary>
	private (Color Dust, Color Chunk) GroundColours() => _kind switch
	{
		Ground.Soil => (new Color( 0.78f, 0.66f, 0.52f ), new Color( 0.5f, 0.41f, 0.32f )),
		Ground.Grass => (new Color( 0.7f, 0.64f, 0.52f ), new Color( 0.44f, 0.39f, 0.31f )),
		Ground.Wood => (new Color( 0.74f, 0.66f, 0.56f ), new Color( 0.5f, 0.4f, 0.3f )),
		_ => (new Color( 0.82f, 0.8f, 0.76f ), new Color( 0.62f, 0.6f, 0.57f )),
	};

	/// <summary>
	/// The detonation's flash, then the fireball: a cube-root scaling of measured high-explosive fireballs gives
	/// ~3.4 m across a kg^(1/3) of TNT, ~8 m for this one, sitting on the ground as a dome.
	/// </summary>
	private void EmitFlashAndFireball()
	{
		var diameter = 3.4f * MathF.Cbrt( ChargeKg * TntEquivalence ) * Ballistics.UnitsPerMeter;
		var centre = _ground + Vector3.Up * (diameter * 0.3f);

		FireballParticles.Emit( _flash, centre, diameter * 1.5f, 0.22f, 0f, 8f, 0f );

		FireballParticles.Emit( _fireball, centre, diameter * 1.05f, Random.Shared.Float( 1.4f, 1.7f ), 0.004f, 4.5f, 70f );
		for ( var i = 0; i < 6; i++ )
		{
			var yaw = i * 60f + Random.Shared.Float( -20f, 20f );
			var offset = Rotation.FromYaw( yaw ).Forward * (diameter * Random.Shared.Float( 0.16f, 0.3f ))
				+ Vector3.Up * (diameter * Random.Shared.Float( -0.12f, 0.2f ));
			FireballParticles.Emit( _fireball, centre + offset, diameter * Random.Shared.Float( 0.65f, 0.85f ),
				Random.Shared.Float( 1.1f, 1.6f ), Random.Shared.Float( 0f, 0.02f ), Random.Shared.Float( 3.5f, 4.5f ),
				Random.Shared.Float( 50f, 90f ) );
		}
		// The skirt of flame rolling out along the ground under it.
		for ( var i = 0; i < 4; i++ )
		{
			var at = _ground + Vector3.Up * (diameter * 0.12f)
				+ Rotation.FromYaw( i * 90f + Random.Shared.Float( 0f, 60f ) ).Forward * (diameter * Random.Shared.Float( 0.35f, 0.45f ));
			FireballParticles.Emit( _fireball, at, diameter * Random.Shared.Float( 0.45f, 0.6f ), Random.Shared.Float( 0.9f, 1.2f ),
				Random.Shared.Float( 0.01f, 0.03f ), 3.5f, 30f );
		}

		// Hot bits of the charge's case and the burning binder.
		for ( var i = 0; i < 60; i++ )
		{
			var direction = Direction( 8f, 85f );
			SparkParticles.Emit( _sparks, centre + direction * 20f, direction * Random.Shared.Float( 1200f, 2800f ),
				Random.Shared.Float( 1.2f, 2.6f ), Random.Shared.Float( 1900f, 2400f ), Random.Shared.Float( 0.1f, 0.3f ),
				Gravity, Random.Shared.Float( 1.5f, 3f ), 1.8f );
		}
	}

	/// <summary>
	/// The ground's dust: a burst thrown up and out with the chunks, the base surge driven along the ground, and the
	/// mushroom of soot and dust rolling up out of the fireball.
	/// </summary>
	private void EmitDust()
	{
		var (dust, _) = GroundColours();
		var soil = _kind == Ground.Masonry ? dust * 0.75f : dust * 1.1f;

		for ( var i = 0; i < 10; i++ )
		{
			var direction = Direction( 20f, 75f );
			BlastCloudParticles.Emit( _soil, _ground + Vector3.Up * 40f + direction * 40f, direction * Random.Shared.Float( 300f, 700f ),
				drag: 2.2f, startSize: 140f, endSize: Random.Shared.Float( 380f, 500f ), life: Random.Shared.Float( 3.2f, 4.5f ),
				lift: 40f, liftTime: 3f, gravity: 0f, soil.WithAlpha( 1f ), peakAlpha: 0.95f, BlastCloudParticles.Sheet.Once );
		}

		// The surge's front slows from the blast's ~25 m/s to a stop: its linear drag puts it 9-15 m out.
		for ( var i = 0; i < 24; i++ )
		{
			var direction = Rotation.FromYaw( i * 15f + Random.Shared.Float( -6f, 6f ) ).Forward;
			BlastCloudParticles.Emit( _surge, _ground + Vector3.Up * Random.Shared.Float( 25f, 50f ) + direction * 60f,
				direction * Random.Shared.Float( 650f, 1100f ) + Vector3.Up * Random.Shared.Float( 0f, 60f ),
				drag: 1.8f, startSize: 110f, endSize: Random.Shared.Float( 300f, 420f ), life: Random.Shared.Float( 7f, 10f ),
				lift: 20f, liftTime: 4f, gravity: 0f, dust, peakAlpha: 0.75f, BlastCloudParticles.Sheet.Once );
		}

		for ( var i = 0; i < 3; i++ )
		{
			var at = _ground + Vector3.Up * 160f + Rotation.FromYaw( i * 120f ).Forward * 60f;
			BlastCloudParticles.Emit( _plume, at, Vector3.Up * 300f, drag: 1.2f, startSize: 400f,
				endSize: Random.Shared.Float( 700f, 900f ), life: Random.Shared.Float( 6f, 8f ), lift: 180f, liftTime: 3f,
				gravity: 0f, new Color( 0.42f, 0.4f, 0.38f ), peakAlpha: 0.85f, BlastCloudParticles.Sheet.Once );
		}

		// A spray of fine grit ahead of the chunks.
		for ( var i = 0; i < 24; i++ )
		{
			var direction = Direction( 20f, 75f );
			BlastCloudParticles.Emit( _grit, _ground + Vector3.Up * 30f, direction * Random.Shared.Float( 900f, 2000f ),
				drag: 2.5f, startSize: 60f, endSize: Random.Shared.Float( 200f, 280f ), life: Random.Shared.Float( 0.9f, 1.6f ),
				lift: 0f, liftTime: 1f, gravity: Gravity, new Color( 0.25f, 0.22f, 0.2f ), peakAlpha: 0.9f,
				BlastCloudParticles.Sheet.None );
		}
	}

	/// <summary>
	/// Chunks of the ground: mostly a few centimetres, a few up to 30, thrown steeply up at 10-45 m/s, the small ones
	/// fastest. Quadratic air drag (<see cref="DebrisParticles"/>) brings most of them down within 30 m.
	/// </summary>
	private void EmitDebris()
	{
		var (_, chunk) = GroundColours();
		var count = _kind == Ground.Grass ? 50 : 80;
		for ( var i = 0; i < count; i++ )
		{
			var share = Random.Shared.Float();
			var size = 2.5f + 9.5f * share * share * share;
			var direction = Direction( 30f, 82f );
			var speed = MathX.Lerp( 1700f, 450f, (size - 2.5f) / 9.5f ) * Random.Shared.Float( 0.6f, 1.1f );
			var at = _ground + Vector3.Up * 12f + Vector3.Random.WithZ( 0f ) * 30f;
			var tint = chunk * Random.Shared.Float( 0.85f, 1.1f );
			DebrisParticles.Emit( _chunks, at, direction * speed, size, Random.Shared.Int( 0, ChunkShapes - 1 ),
				Random.Shared.Float( 14f, 22f ), tint.WithAlpha( 1f ) );
		}
	}

	/// <summary> The column, fed from the fireball's soot first, then from the dust rising off the ground. </summary>
	private void FeedColumn( float t )
	{
		if ( _columnEmitted >= ColumnPuffs || !_column.IsValid() ) return;

		var due = (int)(ColumnPuffs * Math.Clamp( MathF.Sqrt( t / ColumnFeedTime ), 0f, 1f ));
		var (dust, _) = GroundColours();
		while ( _columnEmitted < due )
		{
			var soot = _columnEmitted < ColumnPuffs / 3;
			var at = soot
				? _ground + Vector3.Up * Random.Shared.Float( 150f, 300f ) + Vector3.Random.WithZ( 0f ) * 90f
				: _ground + Vector3.Up * 60f + Rotation.FromYaw( Random.Shared.Float( 0f, 360f ) ).Forward * Random.Shared.Float( 80f, 260f );
			var colour = soot ? new Color( 0.27f, 0.26f, 0.25f ) : dust * 0.72f;
			BlastCloudParticles.Emit( _column, at, Vector3.Up * 120f, drag: 0.8f, startSize: Random.Shared.Float( 200f, 280f ),
				endSize: Random.Shared.Float( 560f, 820f ), life: Random.Shared.Float( 24f, 34f ),
				lift: Random.Shared.Float( 130f, 220f ), liftTime: 4.5f, gravity: 0f, colour, peakAlpha: soot ? 0.9f : 0.75f,
				BlastCloudParticles.Sheet.Loop );
			_columnEmitted++;
		}
	}

	private void CreateLight()
	{
		var go = new GameObject( GameObject, true, "Blast Light" );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.WorldPosition = _ground + Vector3.Up * 120f;
		_light = go.AddComponent<PointLight>();
		_light.Shadows = true;
		_light.Attenuation = 1f;
		_light.Radius = 2600f;
		_light.LightColor = Color.Black;
	}

	/// <summary> The flash, then the fireball's glow as it cools and turns to smoke. </summary>
	private void UpdateLight( float t )
	{
		if ( !_light.IsValid() ) return;
		var brightness = 14f * MathF.Exp( -t / 0.05f ) + 3f * MathF.Exp( -t / 0.45f );
		_light.Enabled = brightness > 0.01f;
		if ( !_light.Enabled ) return;

		var kelvin = 2200f + 1400f * MathF.Exp( -t / 0.15f );
		var colour = FireParticles.Incandescence( kelvin, 1f );
		var peak = MathF.Max( colour.r, 0.001f );
		_light.LightColor = new Color( colour.r / peak, colour.g / peak, colour.b / peak ) * brightness;
		_light.Radius = 1800f + 800f * MathF.Exp( -t / 0.3f );
		_light.WorldPosition = _ground + Vector3.Up * (120f + 100f * t);
	}

	/// <summary> The fireball blackens the ground about as far as it reached, ~10 m across with the soot. </summary>
	private void PlaceScorch()
	{
		var definition = ResourceLibrary.Get<DecalDefinition>( ScorchDecal );
		if ( definition is null ) return;

		var go = new GameObject( GameObject, true, "Blast Scorch" );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.WorldPosition = _ground + Vector3.Up * 8f;
		go.WorldRotation = Rotation.LookAt( Vector3.Down ) * Rotation.FromRoll( Random.Shared.Float( 0f, 360f ) );

		var decal = go.AddComponent<Decal>();
		decal.Decals = new List<DecalDefinition> { definition };
		var size = 400f / MathF.Max( definition.Width, 1f );
		decal.Size = new Vector2( size, size );
		decal.Depth = 96f;
		decal.ColorTint = Color.White;
	}

	/// <summary>
	/// Loose physics objects in the open within 25 m are thrown, by the blast's impulse over their size: ~12 m/s at
	/// 3 m, ~2 m/s at 10 m. Each machine throws the ones it simulates (its own and every local one).
	/// </summary>
	private void ThrowLooseObjects()
	{
		var origin = _ground + Vector3.Up * 16f;
		var reach = 25f * Ballistics.UnitsPerMeter;
		var trace = Scene.Trace.WithoutTags( "trigger", "ragdoll", "playerclip", "player", "movement", BreakableGlass.Tag );
		var thrown = new HashSet<Rigidbody>();

		foreach ( var obj in Scene.FindInPhysics( new Sphere( origin, reach ) ) )
		{
			if ( !obj.IsValid() || obj.GetComponentInParent<Rigidbody>() is not { } body || !thrown.Add( body ) ) continue;
			if ( body.IsProxy || !body.MotionEnabled ) continue;

			var centre = body.WorldPosition;
			var tr = trace.Ray( origin, centre ).Run();
			if ( tr.Hit && tr.GameObject.IsValid() && !body.GameObject.IsDescendant( tr.GameObject ) && tr.GameObject != body.GameObject )
				continue;

			var metres = MathF.Max( centre.Distance( origin ) / Ballistics.UnitsPerMeter, 1.5f );
			var speed = MathF.Min( 2400f / MathF.Pow( metres, 1.5f ), 900f );
			var direction = ((centre - origin).Normal + Vector3.Up * 0.35f).Normal;
			body.Velocity += direction * speed;
			body.AngularVelocity += Vector3.Random * (speed * 0.02f);
		}
	}

	/// <summary>
	/// The view shakes when the blast gets to the viewer, by its peak overpressure there (<see cref="OverpressureKpa"/>):
	/// as hard as it goes inside 6 m, a jolt at 30 m (~9 kPa), a faint thump at 100 m (~2.5 kPa).
	/// </summary>
	private void ScheduleShake()
	{
		var camera = Scene.Camera;
		if ( !camera.IsValid() ) return;

		var distance = camera.WorldPosition.Distance( _ground );
		var kpa = OverpressureKpa( distance / Ballistics.UnitsPerMeter, EquivalentKg );
		_shakeSize = Math.Clamp( 1.2f * MathF.Pow( kpa / 10f, 0.75f ), 0f, 8f );
		if ( _shakeSize < 0.15f ) return;
		_shakeAt = distance / BulletFlyby.SoundSpeed;
	}

	/// <summary>
	/// A blast's peak overpressure, kPa, <paramref name="metres"/> from a charge of <paramref name="tntKg"/> kg of TNT in
	/// the open (<see cref="EquivalentKg"/>): Kinney and Graham's fit, at the scaled distance.
	/// </summary>
	public static float OverpressureKpa( float metres, float tntKg )
	{
		var z = MathF.Max( metres, 0.3f ) / MathF.Cbrt( MathF.Max( tntKg, 0.01f ) );
		var ratio = 808f * (1f + (z / 4.5f) * (z / 4.5f))
			/ (MathF.Sqrt( 1f + (z / 0.048f) * (z / 0.048f) )
			* MathF.Sqrt( 1f + (z / 0.32f) * (z / 0.32f) )
			* MathF.Sqrt( 1f + (z / 1.35f) * (z / 1.35f) ));
		return ratio * 101.325f;
	}

	/// <summary> About 1 psi: most ordinary window panes break. </summary>
	public const float WindowBreakKpa = 6.9f;

	/// <summary>
	/// Breaks every window pane the blast reaches with no wall in between, as far out as it's still
	/// <see cref="WindowBreakKpa"/> (~37 m for the C4). Host only: a pane's break is sent from whoever breaks it.
	/// </summary>
	public static void BreakWindows( Scene scene, Vector3 point, float tntKg, GameObject ignore )
	{
		var metres = 1f;
		while ( metres < 500f && OverpressureKpa( metres, tntKg ) > WindowBreakKpa )
			metres *= 1.02f;

		var trace = scene.Trace.WithoutTags( "trigger", "ragdoll", "corpse", "playerclip", "player", "movement", BreakableGlass.Tag );
		if ( ignore.IsValid() )
			trace = trace.IgnoreGameObjectHierarchy( ignore );

		var from = point + Vector3.Up * 16f;
		BreakableGlass.BreakInBlast( scene.FindInPhysics( new Sphere( from, metres * Ballistics.UnitsPerMeter ) ), from, trace );
	}

	private Vector3 SampleWind( Vector3 at )
	{
		if ( !_wind.IsValid() ) _wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		return _wind.IsValid() && _wind.Active ? _wind.Sample( at ) : Vector3.Zero;
	}

	/// <summary> A random direction between <paramref name="minElevation"/> and <paramref name="maxElevation"/> degrees above level. </summary>
	private static Vector3 Direction( float minElevation, float maxElevation )
	{
		var elevation = Random.Shared.Float( minElevation, maxElevation );
		return Rotation.From( -elevation, Random.Shared.Float( 0f, 360f ), 0f ).Forward;
	}
}

/// <summary>
/// The fireball's sprites and the flash: each swells to full size in a few hundredths of a second, plays its sheet
/// once (white-hot to orange to black smoke), glows far over white while it's hot and rolls up as it cools. Emit with
/// <see cref="Emit"/>.
/// </summary>
[Hide]
public sealed class FireballParticles : ParticleController
{
	/// <summary> The wind (units/s), which carries the smoke as it rises. Set from the main thread. </summary>
	public Vector3 Wind { get; set; }

	/// <summary> Takes this long (s) to reach full size: a high-explosive fireball's growth is over in ~30 ms. </summary>
	private const float GrowTime = 0.05f;

	/// <summary>
	/// A sprite <paramref name="size"/> units across at its fullest that lasts <paramref name="life"/> seconds, starts
	/// <paramref name="delay"/> seconds in, glows <paramref name="heat"/> times over its sheet's own colour at first, and
	/// rises at up to <paramref name="rise"/> units/s once it has cooled.
	/// </summary>
	public static void Emit( ParticleEffect effect, Vector3 at, float size, float life, float delay, float heat, float rise )
	{
		if ( !effect.IsValid() || effect.IsFull ) return;

		var p = effect.Emit( at, Random.Shared.Float() );
		p.StartScale = life;
		p.HitNormal = new Vector3( size, heat, rise );
		p.HitPos = new Vector3( delay, Random.Shared.Float( -25f, 25f ), 0f );
		p.Size = 0f;
		p.Alpha = 0f;
		p.Color = Color.White;
		p.Sequence = 0;
		p.SequenceTime = Vector3.Zero;
		p.Angles = new Angles( 0f, 0f, Random.Shared.Float( 0f, 360f ) );
		p.Velocity = Vector3.Zero;
	}

	private float _dt;

	protected override void OnBeforeStep( float delta ) => _dt = delta;

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var shape = p.HitNormal;
		var age = p.Age - p.HitPos.x;
		if ( age < 0f )
		{
			p.Alpha = 0f;
			return;
		}

		var life = MathF.Max( p.StartScale, 0.05f );
		var t = age / life;
		if ( t >= 1f )
		{
			p.Alpha = 0f;
			p.Age = 1e6f;
			return;
		}

		var grow = age < GrowTime ? 0.35f + 0.65f * (1f - MathF.Pow( 1f - age / GrowTime, 2f )) : 1f + 0.25f * (age - GrowTime) / life;
		p.Size = shape.x * grow;
		p.SequenceTime.y = MathF.Min( t, 0.995f );

		// White-hot for the first tenth of a second, then the sheet's own colours, a little darker as it turns to soot.
		var glow = 1f + (shape.y - 1f) * MathF.Exp( -age / 0.08f );
		var soot = 1f - 0.25f * Math.Clamp( (t - 0.2f) / 0.3f, 0f, 1f );
		p.Color = new Color( glow * soot, glow * soot, glow * soot );
		p.Alpha = t > 0.6f ? (1f - t) / 0.4f : 1f;
		p.Angles.roll += p.HitPos.y * _dt;

		// Hot gas rises once the blast's own push is spent, and the wind takes it.
		var lift = shape.z * Math.Clamp( (age - 0.12f) / 0.4f, 0f, 1f );
		p.Velocity = Vector3.Up * lift + Wind * 0.4f * Math.Clamp( age, 0f, 1f );
	}
}

/// <summary>
/// Dust and smoke from a blast: thrown out and slowed by the air (linear drag towards the wind), buoyant while it's
/// hot, swelling as it mixes and thinning out over its life. Emit with <see cref="Emit"/>.
/// </summary>
[Hide]
public sealed class BlastCloudParticles : ParticleController
{
	public enum Sheet
	{
		/// <summary> The sheet's first frame only. </summary>
		None,
		/// <summary> The sheet once, over the particle's life. </summary>
		Once,
		/// <summary> A looping sheet, at 8 frames a second. </summary>
		Loop,
	}

	/// <summary> The wind (units/s). Set from the main thread. </summary>
	public Vector3 Wind { get; set; }

	private float _dt;
	private float _time;

	protected override void OnBeforeStep( float delta )
	{
		_dt = delta;
		_time += delta;
	}

	/// <summary>
	/// A puff starting at <paramref name="velocity"/>, slowed towards the wind at <paramref name="drag"/> (1/s), that
	/// grows from <paramref name="startSize"/> to <paramref name="endSize"/> units over <paramref name="life"/> seconds,
	/// rises at up to <paramref name="lift"/> units/s easing off over <paramref name="liftTime"/> seconds, and falls with
	/// <paramref name="gravity"/> (units/s², for grit).
	/// </summary>
	public static void Emit( ParticleEffect effect, Vector3 at, Vector3 velocity, float drag, float startSize, float endSize,
		float life, float lift, float liftTime, float gravity, Color color, float peakAlpha, Sheet sheet )
	{
		if ( !effect.IsValid() || effect.IsFull ) return;

		var p = effect.Emit( at, Random.Shared.Float() );
		p.StartScale = life;
		p.HitNormal = new Vector3( startSize, endSize, peakAlpha );
		p.HitPos = new Vector3( drag, lift, gravity );
		p.StartAngles = new Angles( Random.Shared.Float( -15f, 15f ), (int)sheet, MathF.Max( liftTime, 0.1f ) );
		p.Color = color.WithAlpha( 1f );
		p.Alpha = 0f;
		p.Size = startSize;
		p.Sequence = 0;
		p.SequenceTime = new Vector3( 0f, 0f, sheet == Sheet.Loop ? Random.Shared.Float() : 0f );
		p.Angles = new Angles( 0f, 0f, Random.Shared.Float( 0f, 360f ) );
		p.Velocity = velocity;
	}

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var t = p.Age / MathF.Max( p.StartScale, 0.05f );
		if ( t >= 1f )
		{
			p.Alpha = 0f;
			p.Age = 1e6f;
			return;
		}

		var shape = p.HitNormal;
		var motion = p.HitPos;
		var extra = p.StartAngles;

		var swell = 1f - (1f - t) * (1f - t) * (1f - t);
		p.Size = MathX.Lerp( shape.x, shape.y, swell );
		p.Alpha = shape.z * (t < 0.04f ? t / 0.04f : t > 0.45f ? MathF.Pow( (1f - t) / 0.55f, 1.3f ) : 1f);
		p.Angles.roll += extra.pitch * _dt;
		p.SequenceTime.y = (Sheet)(int)extra.yaw switch
		{
			Sheet.Once => MathF.Min( t, 0.995f ),
			Sheet.Loop => p.Age * 8f / 64f,
			_ => 0f,
		};

		var q = p.Position / 120f;
		var eddy = new Vector3(
			MathF.Sin( q.z + _time * 0.5f ) + MathF.Cos( q.y - _time * 0.4f ),
			MathF.Sin( q.x + _time * 0.45f ) + MathF.Cos( q.z + _time * 0.35f ),
			MathF.Sin( q.y - _time * 0.3f ) * 0.5f ) * 8f;
		var target = Wind + Vector3.Up * (motion.y * MathF.Exp( -p.Age / extra.roll )) + eddy;
		p.Velocity += (target - p.Velocity) * (1f - MathF.Exp( -_dt * motion.x )) + Vector3.Down * (motion.z * _dt);
	}
}

/// <summary>
/// Chunks of the ground thrown by a blast: ballistic under real gravity with quadratic air drag for a stone of their
/// size, tumbling while they fly, and lying where they land until they fade. Emit with <see cref="Emit"/>.
/// </summary>
[Hide]
public sealed class DebrisParticles : ParticleController
{
	/// <summary> Stone, kg/m³. </summary>
	private const float Density = 2400f;

	/// <summary> A rough lump's drag coefficient. </summary>
	private const float DragCoefficient = 1f;

	/// <summary> Air, kg/m³. </summary>
	private const float AirDensity = 1.225f;

	/// <summary> A chunk takes this long (s) to fade once its time is up. </summary>
	private const float FadeTime = 1.5f;

	private float _dt;

	protected override void OnBeforeStep( float delta ) => _dt = delta;

	/// <summary>
	/// A chunk <paramref name="size"/> units across (its sprite's width: the stone is about 0.6 of it) of shape
	/// <paramref name="shape"/> on the sheet, lying there for <paramref name="life"/> seconds.
	/// </summary>
	public static void Emit( ParticleEffect effect, Vector3 at, Vector3 velocity, float size, int shape, float life, Color tint )
	{
		if ( !effect.IsValid() || effect.IsFull ) return;

		var p = effect.Emit( at, Random.Shared.Float() );
		// The effect collides, which uses HitPos and HitNormal, so these go in StartScale and StartAngles.
		var metres = 0.6f * size / Ballistics.UnitsPerMeter;
		// k = rho Cd A / 2m for a sphere, per unit: the drag's deceleration is k |v| v.
		var k = 3f * AirDensity * DragCoefficient / (4f * Density * metres) / Ballistics.UnitsPerMeter;
		p.StartScale = size;
		p.StartAngles = new Angles( Random.Shared.Float( 200f, 900f ) * (Random.Shared.Float() < 0.5f ? -1f : 1f), life, k );
		p.Size = size;
		p.Color = tint;
		p.Alpha = 1f;
		p.Sequence = shape;
		p.SequenceTime = Vector3.Zero;
		p.Angles = new Angles( 0f, 0f, Random.Shared.Float( 0f, 360f ) );
		p.Velocity = velocity;
	}

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var data = p.StartAngles;
		var past = p.Age - data.yaw;
		if ( past >= FadeTime )
		{
			p.Alpha = 0f;
			p.Age = 1e6f;
			return;
		}

		p.Alpha = past > 0f ? 1f - past / FadeTime : 1f;
		var speed = p.Velocity.Length;
		p.Velocity += (Vector3.Down * DemolitionBlast.Gravity - p.Velocity * (data.roll * speed)) * _dt;
		p.Angles.roll += data.pitch * Math.Clamp( speed / 300f, 0f, 1f ) * _dt;
	}
}
