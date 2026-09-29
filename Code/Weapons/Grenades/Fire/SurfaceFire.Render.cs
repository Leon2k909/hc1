namespace Facepunch;

/// <summary>
/// Drawing the fire on each machine: flames, smoke and embers from every burning cell, firelight and crackling from the
/// biggest patches near the camera, and scorch marks where it has burnt.
/// </summary>
public sealed partial class SurfaceFire
{
	private const string FireLoopSound = "sounds/weapons/grenade/molotov_fire_loop.sound";

	/// <summary> Flames a second from a fully burning cell. Each lives under a second, so a few are up at once. </summary>
	private const float FlamesPerSecond = 7f;
	private const float SmokePerSecond = 0.7f;
	private const float EmbersPerSecond = 0.35f;

	/// <summary> Past this far from the camera, cells emit fewer, bigger flames. </summary>
	private const float DetailDistance = 1500f;

	private const int MaxLights = 6;
	private const int MaxLoops = 3;
	private const int MaxScorchDecals = 600;

	/// <summary> Nearby burning cells are pooled for light and sound, in squares this many cells across. </summary>
	private const int LightCluster = 6;
	private const int SoundCluster = 12;

	/// <summary> Burnt ground that isn't terrain grass: floorboards, cloth, lawn, and terrain that can't be painted. </summary>
	private const string BurntPatchDecal = "decals/fire/burnt_patch.decal";

	/// <summary> Where thermite burnt out: a puddle of slag in a black scorch, with drops of iron round it. </summary>
	private const string ThermiteScorchDecal = "decals/fire/thermite_scorch.decal";

	private GameObject _visuals;
	private ParticleEffect _flames;
	private ParticleEffect _smoke;
	private ParticleEffect _embers;
	private readonly PointLight[] _lights = new PointLight[MaxLights];
	private readonly SoundHandle[] _loops = new SoundHandle[MaxLoops];
	private GameObject _scorchRoot;
	private readonly List<GameObject> _scorchDecals = new();
	private readonly Dictionary<long, (Vector3 Sum, float Weight, float Top)> _clusters = new();
	private readonly List<(Vector3 Position, float Weight, float Top)> _ranked = new();

	private void EnsureVisuals()
	{
		if ( _visuals.IsValid() ) return;

		_visuals = new GameObject( GameObject, true, "Fire Visuals" );
		_visuals.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		_visuals.NetworkMode = NetworkMode.Never;

		_flames = FireParticles.Create<FlameParticles>( _visuals, "Flames", FireParticles.Flame, 4000,
			additive: true, upright: true, feather: 12f );
		_smoke = FireParticles.Create<FireSmokeParticles>( _visuals, "Smoke", FireParticles.Smoke, 1500,
			additive: false, lit: true, sorted: true, feather: 24f );
		_embers = FireParticles.Create<SparkParticles>( _visuals, "Embers", FireParticles.Ember, 600,
			additive: true, feather: 0f );

		var embers = _embers.GetComponent<ParticleSpriteRenderer>();
		embers.MotionBlur = true;
		embers.LeadingTrail = false;
		embers.BlurAmount = 0.5f;
		embers.BlurSpacing = 0.6f;
		embers.BlurOpacity = 0.7f;
	}

	private void Render()
	{
		var now = Time.Now;
		var dt = Time.Delta;

		if ( _burning.Count == 0 )
		{
			HideLightsAndSound();
			return;
		}

		EnsureVisuals();

		var camera = Scene.Camera.IsValid() ? Scene.Camera.WorldPosition : Vector3.Zero;
		var wind = SampleWind();
		_flames.GetComponent<FlameParticles>().Wind = wind;
		_smoke.GetComponent<FireSmokeParticles>().Wind = wind;
		_embers.GetComponent<SparkParticles>().Wind = wind;

		// Past a share of each effect's budget, every cell emits less, so a big fire thins out rather than cutting off.
		var flameBudget = Budget( _flames );
		var smokeBudget = Budget( _smoke );
		var emberBudget = Budget( _embers );

		_clusters.Clear();
		var centre = Vector3.Zero;

		for ( var i = 0; i < _burning.Count; i++ )
		{
			var burning = _burning[i];
			var envelope = Envelope( burning, now );
			centre += burning.Ground;
			if ( envelope < 0.02f ) continue;

			var height = burning.Flame * envelope * FireFuels.Metre;
			var distance = burning.Ground.Distance( camera );
			var detail = distance < DetailDistance ? 1f : MathF.Max( 0.25f, DetailDistance / distance );

			burning.FlameDebt += FlamesPerSecond * detail * flameBudget * dt;
			while ( burning.FlameDebt >= 1f )
			{
				burning.FlameDebt -= 1f;
				EmitFlame( burning, height, detail );
			}

			var smoky = burning.Fuel is FireFuel.Wood or FireFuel.Fabric ? 1.3f : 1f;
			burning.SmokeDebt += SmokePerSecond * smoky * envelope * smokeBudget * dt;
			while ( burning.SmokeDebt >= 1f )
			{
				burning.SmokeDebt -= 1f;
				EmitSmoke( burning, height );
			}

			burning.EmberDebt += EmbersPerSecond * envelope * detail * emberBudget * dt;
			while ( burning.EmberDebt >= 1f )
			{
				burning.EmberDebt -= 1f;
				EmitEmber( burning, height );
			}

			_burning[i] = burning;
			AddToCluster( burning, envelope, height );
		}

		// The effects' bounds are measured from their origin, so keep it among the flames.
		_visuals.WorldPosition = centre / _burning.Count;

		UpdateLights( camera, now );
		UpdateLoops( camera );
	}

	private static float Budget( ParticleEffect effect )
	{
		var used = effect.ParticleCount / (float)effect.MaxParticles;
		return Math.Clamp( 1f - (used - 0.6f) / 0.4f, 0.1f, 1f );
	}

	private Vector3 SampleWind()
	{
		if ( !_wind.IsValid() ) _wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		return _wind.IsValid() && _wind.Active ? _wind.Sample( _visuals.WorldPosition ) : Vector3.Zero;
	}

	private void EmitFlame( in Burning burning, float height, float detail )
	{
		var random = Random.Shared;
		var tall = height * random.Float( 0.7f, 1.25f ) / MathF.Sqrt( detail );
		var wide = Math.Clamp( tall / FireParticles.FlameAspect * 1.1f, 6f, CellSize * 1.6f );
		var spot = burning.Ground + new Vector3( random.Float( -0.5f, 0.5f ) * CellSize, random.Float( -0.5f, 0.5f ) * CellSize, 0f );
		var life = random.Float( 0.45f, 0.8f ) * MathF.Sqrt( MathF.Max( tall, 10f ) / 50f );

		// Bright yellow at the base, as the sheet already is; a little dimmer for the smoky wood and cloth fires.
		var glow = burning.Fuel is FireFuel.Wood or FireFuel.Fabric ? 1.2f : 1.5f;
		FlameParticles.Emit( _flames, spot, wide, tall, life, new Color( glow, glow * 0.9f, glow * 0.8f, 1f ) );
	}

	private void EmitSmoke( in Burning burning, float height )
	{
		var random = Random.Shared;
		var at = burning.Ground + new Vector3( random.Float( -20f, 20f ), random.Float( -20f, 20f ), height * 0.8f + 10f );

		// Grass smoke is pale grey-brown; wood and cloth burn smokier and darker.
		var dark = burning.Fuel is FireFuel.Wood or FireFuel.Fabric;
		var shade = dark ? random.Float( 0.25f, 0.35f ) : random.Float( 0.55f, 0.65f );
		var color = new Color( shade, shade * 0.96f, shade * 0.9f, dark ? 0.55f : 0.4f );
		FireSmokeParticles.Emit( _smoke, at, random.Float( 30f, 50f ), random.Float( 160f, 260f ),
			random.Float( 70f, 120f ), random.Float( 7f, 11f ), color );
	}

	private void EmitEmber( in Burning burning, float height )
	{
		var random = Random.Shared;
		var at = burning.Ground + new Vector3( random.Float( -15f, 15f ), random.Float( -15f, 15f ), height * random.Float( 0.3f, 0.9f ) );
		var velocity = new Vector3( random.Float( -30f, 30f ), random.Float( -30f, 30f ), random.Float( 90f, 200f ) );

		// Bits of burning grass: carried up by the flames, drifting with the wind, glowing for a second or two.
		SparkParticles.Emit( _embers, at, velocity, random.Float( 0.8f, 1.6f ), random.Float( 1150f, 1350f ),
			random.Float( 1.2f, 2.5f ), gravity: 60f, drag: 1.5f, brightness: 8f );
	}

	private void AddToCluster( in Burning burning, float envelope, float height )
	{
		var (ix, iy, iz) = Unpack( burning.Key );
		var key = Pack( FloorDiv( ix, LightCluster ), FloorDiv( iy, LightCluster ), iz );
		var weight = envelope * burning.Flame;
		var cluster = _clusters.GetValueOrDefault( key );
		_clusters[key] = (cluster.Sum + burning.Ground * weight, cluster.Weight + weight, MathF.Max( cluster.Top, height ));
	}

	/// <summary> Firelight from the brightest patches near the camera, flickering as the flames do. </summary>
	private void UpdateLights( Vector3 camera, float now )
	{
		RankClusters( camera, _clusters );

		for ( var i = 0; i < MaxLights; i++ )
		{
			if ( i >= _ranked.Count )
			{
				if ( _lights[i].IsValid() ) _lights[i].Enabled = false;
				continue;
			}

			var (position, weight, top) = _ranked[i];
			var light = _lights[i] ??= CreateLight( i );
			light.Enabled = true;
			light.WorldPosition = position + Vector3.Up * (top * 0.6f + 12f);

			var flicker = 0.8f + 0.12f * MathF.Sin( now * 13.1f + i * 1.7f ) + 0.08f * MathF.Sin( now * 29.3f + i * 4.1f );
			var strength = MathF.Sqrt( weight ) * flicker;
			light.Radius = 120f + 220f * MathF.Sqrt( weight );
			light.LightColor = new Color( 1f, 0.5f, 0.18f ) * (1.2f * strength);
		}
	}

	private PointLight CreateLight( int index )
	{
		var go = new GameObject( _visuals, true, $"Firelight {index}" );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		var light = go.AddComponent<PointLight>();
		light.Shadows = false;
		light.Attenuation = 2f;
		return light;
	}

	/// <summary> The fire's roar and crackle from the biggest patches near the camera. </summary>
	private void UpdateLoops( Vector3 camera )
	{
		// Pool the light clusters into bigger ones for sound.
		var sounds = new Dictionary<long, (Vector3 Sum, float Weight, float Top)>();
		foreach ( var (key, cluster) in _clusters )
		{
			var (ix, iy, iz) = Unpack( key );
			var big = Pack( FloorDiv( ix, SoundCluster / LightCluster ), FloorDiv( iy, SoundCluster / LightCluster ), iz );
			var existing = sounds.GetValueOrDefault( big );
			sounds[big] = (existing.Sum + cluster.Sum, existing.Weight + cluster.Weight, MathF.Max( existing.Top, cluster.Top ));
		}

		RankClusters( camera, sounds );

		for ( var i = 0; i < MaxLoops; i++ )
		{
			if ( i >= _ranked.Count )
			{
				StopLoop( i );
				continue;
			}

			var (position, weight, _) = _ranked[i];
			if ( _loops[i] is null || !_loops[i].IsValid || _loops[i].IsStopped )
				_loops[i] = Sound.Play( FireLoopSound, position );

			if ( _loops[i] is null || !_loops[i].IsValid ) continue;
			_loops[i].Position = position;
			_loops[i].Volume = Math.Clamp( 0.25f + MathF.Sqrt( weight ) * 0.25f, 0.25f, 1f );
		}
	}

	private void StopLoop( int index )
	{
		if ( _loops[index] is not null && _loops[index].IsValid && !_loops[index].IsStopped )
			_loops[index].Stop( 1.5f );
		_loops[index] = null;
	}

	/// <summary> Clusters, strongest first by how much they'd light or be heard at the camera. </summary>
	private void RankClusters( Vector3 camera, Dictionary<long, (Vector3 Sum, float Weight, float Top)> clusters )
	{
		_ranked.Clear();
		foreach ( var cluster in clusters.Values )
		{
			if ( cluster.Weight <= 0.01f ) continue;
			_ranked.Add( (cluster.Sum / cluster.Weight, cluster.Weight, cluster.Top) );
		}

		_ranked.Sort( ( a, b ) =>
			(b.Weight / (1f + b.Position.DistanceSquared( camera ) / 250000f))
			.CompareTo( a.Weight / (1f + a.Position.DistanceSquared( camera ) / 250000f) ) );
	}

	private void HideLightsAndSound()
	{
		foreach ( var light in _lights )
		{
			if ( light.IsValid() ) light.Enabled = false;
		}

		for ( var i = 0; i < MaxLoops; i++ ) StopLoop( i );
	}

	/// <summary>
	/// A scorch mark, projected down onto whatever is there. Its box is only as deep as the ground under it is uneven, so
	/// it doesn't paint the legs of whoever stands on it.
	/// </summary>
	private void PlaceScorchDecal( ScorchMark mark )
	{
		if ( _scorchDecals.Count >= MaxScorchDecals ) return;

		var definition = ResourceLibrary.Get<DecalDefinition>( mark.Kind == ScorchKind.Thermite ? ThermiteScorchDecal : BurntPatchDecal );
		if ( definition is null ) return;

		if ( !_scorchRoot.IsValid() )
		{
			// Not under the flames' object, which follows the fire about.
			_scorchRoot = new GameObject( GameObject, true, "Scorch Marks" );
			_scorchRoot.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			_scorchRoot.NetworkMode = NetworkMode.Never;
		}

		var (low, high) = GroundRange( mark.Position, mark.Width * 0.5f );

		var go = new GameObject( _scorchRoot, true, "Scorch" );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.WorldPosition = mark.Position.WithZ( (low + high) * 0.5f );
		go.WorldRotation = Rotation.LookAt( Vector3.Down );

		var decal = go.AddComponent<Decal>();
		decal.Decals = new List<DecalDefinition> { definition };
		var size = mark.Width / MathF.Max( definition.Width, 1f );
		decal.Size = new Vector2( size, size );
		decal.Depth = high - low + 8f;
		decal.ColorTint = Color.White;
		_scorchDecals.Add( go );
	}

	/// <summary> The lowest and highest ground under a mark, from its middle and four corners. </summary>
	private (float Low, float High) GroundRange( Vector3 centre, float half )
	{
		var low = centre.z;
		var high = centre.z;
		for ( var i = 0; i < 4; i++ )
		{
			var corner = centre + new Vector3( (i & 1) == 0 ? -half : half, (i & 2) == 0 ? -half : half, 0f );
			var tr = Trace( corner + Vector3.Up * (half + 16f), corner + Vector3.Down * (half + 16f) );
			if ( !tr.Hit || tr.StartedSolid ) continue;
			low = MathF.Min( low, tr.HitPosition.z );
			high = MathF.Max( high, tr.HitPosition.z );
		}

		return (low, high);
	}

	private void DestroyVisuals()
	{
		for ( var i = 0; i < MaxLoops; i++ ) StopLoop( i );
		if ( _visuals.IsValid() ) _visuals.Destroy();
		if ( _scorchRoot.IsValid() ) _scorchRoot.Destroy();
		_scorchDecals.Clear();
		RestoreTerrain();
	}
}
