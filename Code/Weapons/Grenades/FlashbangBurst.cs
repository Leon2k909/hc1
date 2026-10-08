namespace Facepunch;

/// <summary>
/// The flashbang's visible detonation, separate from the viewer's blindness and hearing effects.
/// A frame-integrated light pulse illuminates the scene; a small soft source and lit smoke have no opaque fallback.
/// </summary>
[Title( "Flashbang Burst" )]
public sealed class FlashbangBurst : Component
{
	// The measured light pulse is shorter than a normal frame. Integrate it into the first frame so it is
	// visible at every frame rate, without stretching the physical light into a lingering fireball.
	private const float PulseSeconds = .009f;
	private const float PeakBrightness = 100f;
	private const float LightRadius = 1100f;
	// A single alpha-masked puff from the engine's smoke_static_a sheet, without the neighbouring atlas cells.
	private const string SmokeTexture = "textures/particles/hc1_flashbang_smoke.vtex";

	private PointLight _light;
	private TimeSince _sinceStart;
	private ulong _firstFrame;

	protected override void OnStart()
	{
		_sinceStart = 0;
		_firstFrame = Application.FrameCount;
		CreateBurst();
		UpdateLight( 0f, Time.Delta );
	}

	protected override void OnUpdate()
	{
		if ( Application.FrameCount != _firstFrame )
			UpdateLight( _sinceStart, Time.Delta );
	}

	private void CreateBurst()
	{
		var at = WorldPosition + Vector3.Up * 6f;
		var lightObject = new GameObject( GameObject, true, "Flash Light" );
		lightObject.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		lightObject.NetworkMode = NetworkMode.Never;
		lightObject.WorldPosition = at;
		_light = lightObject.AddComponent<PointLight>();
		_light.Shadows = true;
		_light.Attenuation = 1f;
		_light.Radius = LightRadius;

		var glow = Create<FlashbangGlowParticles>( "Flash Source", FireParticles.Glow, 1, additive: true );
		if ( glow.IsValid() )
		{
			var p = glow.Emit( at, 0f );
			p.StartScale = MathF.Max( .025f, Time.Delta * 2f );
			p.Size = 24f;
			p.Color = new Color( 1f, .97f, .91f ) * 24f;
			p.Alpha = 1f;
		}

		var smoke = Create<BlastCloudParticles>( "Residual Smoke", SmokeTexture, 7, additive: false, lit: true );
		if ( !smoke.IsValid() ) return;
		for ( int k = 0; k < 7; k++ )
		{
			var direction = Rotation.FromYaw( k * 360f / 7f + Random.Shared.Float( -15f, 15f ) ).Forward;
			var velocity = direction * Random.Shared.Float( 80f, 135f ) + Vector3.Up * Random.Shared.Float( 16f, 40f );
			BlastCloudParticles.Emit( smoke, at + direction * 2f, velocity, drag: 4f,
				startSize: Random.Shared.Float( 9f, 14f ), endSize: Random.Shared.Float( 38f, 58f ),
				life: Random.Shared.Float( 1.3f, 2.2f ), lift: 16f, liftTime: .6f, gravity: 0f,
				new Color( .76f, .74f, .7f ), peakAlpha: Random.Shared.Float( .13f, .22f ), BlastCloudParticles.Sheet.None );
		}
	}

	/// <summary>Skip a missing texture rather than ever rendering its rectangular fallback.</summary>
	private ParticleEffect Create<T>( string name, string path, int count, bool additive, bool lit = false )
		where T : ParticleController, new()
	{
		var texture = Texture.Load( path );
		if ( texture is null || texture.IsError ) return null;
		return FireParticles.Create<T>( GameObject, name, path, count, additive, lit,
			sorted: !additive, feather: additive ? 2f : 12f );
	}

	private void UpdateLight( float elapsed, float delta )
	{
		if ( !_light.IsValid() ) return;
		var share = Math.Clamp( (PulseSeconds - elapsed) / MathF.Max( delta, .0001f ), 0f, 1f );
		_light.Enabled = share > 0f;
		_light.LightColor = new Color( 1f, .97f, .91f ) * (PeakBrightness * share);
	}
}

/// <summary>A compact, additive source with a feathered glow texture and a very short optical tail.</summary>
[Hide]
public sealed class FlashbangGlowParticles : ParticleController
{
	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var t = p.Age / MathF.Max( p.StartScale, .009f );
		if ( t >= 1f )
		{
			p.Alpha = 0f;
			p.Age = 1e6f;
			return;
		}
		p.Size = 24f + 8f * t;
		p.Alpha = MathF.Exp( -4f * t );
	}
}
