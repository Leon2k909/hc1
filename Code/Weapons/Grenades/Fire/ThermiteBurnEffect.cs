namespace Facepunch;

/// <summary>
/// What a burning <see cref="ThermiteGrenade"/> looks and sounds like, on each machine. Thermate burns at about 2,200 C,
/// hot enough to look white: a glare too bright to look at, a fountain of sparks from the canister's top, drops of
/// molten iron running off and skittering over the ground, thick white smoke, and a pool of slag that glows yellow
/// under it and cools through orange and red for half a minute after. The light is the burn's own colour, about
/// 2,500 K, and it throws hard, flickering shadows.
/// </summary>
[Hide]
public sealed class ThermiteBurnEffect : Component
{
	private const string IgniteSound = "sounds/weapons/grenade/thermite_ignite.sound";
	private const string BurnSound = "sounds/weapons/grenade/thermite_burn.sound";
	// This texture fades continuously from the centre; glow_simple_01 has a broad, solid-looking disc.
	private const string SoftGlowTexture = "textures/particles/particle_glow_05.vtex";

	/// <summary> Sparks a second at full burn, and how fast they leave the vents (units/s). </summary>
	private const float SparksPerSecond = 150f;
	private const float SparkSpeedMin = 100f;
	private const float SparkSpeedMax = 350f;

	/// <summary> Drops of molten iron a second at full burn: fewer, heavier, slower, and they glow for seconds. </summary>
	private const float DropsPerSecond = 8f;

	private const float FlamesPerSecond = 30f;
	private const float SmokePerSecond = 6f;

	/// <summary> The slag pool cools from this (K) with this time constant (s) once the charge has burnt out. </summary>
	private const float PoolKelvin = 2300f;
	private const float PoolCooling = 25f;

	/// <summary> Below this a glow can't be seen in daylight (Draper point, ~800 K). </summary>
	private const float GlowKelvin = 800f;

	/// <summary> Standard gravity, in units/s². </summary>
	private const float Gravity = 386f;

	public ThermiteGrenade Grenade { get; set; }

	private ParticleEffect _sparks;
	private ParticleEffect _drops;
	private ParticleEffect _flames;
	private ParticleEffect _smoke;
	private SpriteRenderer _core;
	private SpriteRenderer _halo;
	private SpriteRenderer _pool;
	private PointLight _light;
	private SoundHandle _loop;
	private WorldWind _wind;

	private float _sparkDebt;
	private float _dropDebt;
	private float _flameDebt;
	private float _smokeDebt;
	private Vector3 _ground;
	private bool _hasGround;
	private TimeSince _sinceGroundCheck;
	private bool _ignitePlayed;

	protected override void OnStart()
	{
		var root = GameObject;
		_sparks = FireParticles.Create<SparkParticles>( root, "Sparks", FireParticles.Spark, 500, additive: true, feather: 0f );
		_drops = FireParticles.Create<SparkParticles>( root, "Molten Iron", FireParticles.Glow, 200, additive: true, feather: 0f );
		_flames = FireParticles.Create<FlameParticles>( root, "Flame", FireParticles.Flame, 60, additive: true, upright: true, feather: 4f );
		_smoke = FireParticles.Create<FireSmokeParticles>( root, "Smoke", FireParticles.Smoke, 250, additive: false, lit: true, sorted: true, feather: 24f );

		// Sparks and drops hit the ground and bounce or run along it. Sparks skip off; molten iron splats and slides.
		foreach ( var (effect, bounce, friction) in new[] { (_sparks, 0.35f, 0.6f), (_drops, 0.05f, 1.5f) } )
		{
			effect.Collision = true;
			effect.CollisionRadius = 0.5f;
			effect.Bounce = bounce;
			effect.Friction = friction;
			effect.CollisionIgnore = new TagSet( new[] { "trigger", "playerclip", "grenade", "particles", "movement", "player", "ragdoll", "corpse" } );

			var renderer = effect.GetComponent<ParticleSpriteRenderer>();
			renderer.MotionBlur = true;
			renderer.LeadingTrail = false;
			renderer.BlurAmount = 0.6f;
			renderer.BlurSpacing = 0.5f;
			renderer.BlurOpacity = 0.8f;
		}

		_core = CreateGlow( "Glare", 10f );
		_halo = CreateGlow( "Halo", 32f );
		_halo.DepthFeather = 12f;

		// The pool lies flat on the ground: a sprite facing up, a hair above it so the ground doesn't cut through it.
		_pool = CreateGlow( "Slag Pool", 8f );
		_pool.Billboard = SpriteRenderer.BillboardMode.None;
		_pool.DepthFeather = 0f;

		var lightObject = new GameObject( GameObject, true, "Thermite Light" );
		lightObject.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		lightObject.NetworkMode = NetworkMode.Never;
		_light = lightObject.AddComponent<PointLight>();
		_light.Shadows = true;
		_light.Attenuation = 1f;
		_light.Radius = 800f;
		_light.LightColor = Color.Black;
	}

	private SpriteRenderer CreateGlow( string name, float size )
	{
		var go = new GameObject( GameObject, true, name );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.Tags.Add( "particles" );

		var sprite = go.AddComponent<SpriteRenderer>();
		sprite.Sprite = FireParticles.SpriteOf( SoftGlowTexture );
		sprite.Size = new Vector2( size, size );
		sprite.Additive = true;
		sprite.Lighting = false;
		sprite.Shadows = false;
		sprite.DepthFeather = 4f;
		sprite.Billboard = SpriteRenderer.BillboardMode.Always;
		sprite.Color = Color.Black;
		return sprite;
	}

	protected override void OnDestroy()
	{
		if ( _loop is not null && _loop.IsValid && !_loop.IsStopped )
			_loop.Stop( 0.5f );
		_loop = null;
	}

	protected override void OnUpdate()
	{
		var grenade = Grenade;
		if ( !grenade.IsValid() || !grenade.Ignited )
			return;

		float t = grenade.SinceIgnited;
		var intensity = ThermiteGrenade.Intensity( t );
		var dt = Time.Delta;
		var now = Time.Now;

		var axis = grenade.WorldRotation.Up;
		var top = grenade.WorldTransform.PointToWorld( ThermiteGrenade.LocalTop );
		UpdateGround( grenade );

		var wind = SampleWind( top );
		_sparks.GetComponent<SparkParticles>().Wind = wind;
		_drops.GetComponent<SparkParticles>().Wind = wind;
		_flames.GetComponent<FlameParticles>().Wind = wind;
		_smoke.GetComponent<FireSmokeParticles>().Wind = wind;

		// The burn itself: a white-hot glare, flickering fast as the reaction sputters.
		var flicker = 0.9f + 0.06f * MathF.Sin( now * 31f ) + 0.04f * MathF.Sin( now * 47f + 1.3f )
			+ Random.Shared.Float( -0.04f, 0.04f );
		var glare = intensity * flicker;
		_core.WorldPosition = top;
		_core.Color = new Color( 12f, 11f, 9f ) * glare;
		_core.Size = new Vector2( 10f, 10f ) * (0.8f + 0.2f * flicker);
		_halo.WorldPosition = top;
		_halo.Color = new Color( 0.6f, 0.28f, 0.1f ) * glare;

		UpdatePool( t, intensity );
		UpdateLight( top, axis, t, glare );
		UpdateSound( top, intensity );

		if ( intensity <= 0f )
		{
			// A wisp of smoke off the cooling slag for a while after.
			if ( t > ThermiteGrenade.BurnTime && t < ThermiteGrenade.BurnTime + 20f )
			{
				_smokeDebt += dt * (1f - (t - ThermiteGrenade.BurnTime) / 20f);
				while ( _smokeDebt >= 1f )
				{
					_smokeDebt -= 1f;
					EmitSmoke( PoolCentre( top ), 0.3f );
				}
			}

			return;
		}

		_sparkDebt += SparksPerSecond * intensity * dt;
		while ( _sparkDebt >= 1f )
		{
			_sparkDebt -= 1f;
			EmitSpark( top, axis );
		}

		_dropDebt += DropsPerSecond * intensity * dt;
		while ( _dropDebt >= 1f )
		{
			_dropDebt -= 1f;
			EmitDrop( top, axis );
		}

		_flameDebt += FlamesPerSecond * intensity * dt;
		while ( _flameDebt >= 1f )
		{
			_flameDebt -= 1f;
			EmitFlame( top, intensity );
		}

		_smokeDebt += SmokePerSecond * intensity * dt;
		while ( _smokeDebt >= 1f )
		{
			_smokeDebt -= 1f;
			EmitSmoke( top, 1f );
		}
	}

	/// <summary> The ground under the canister, looked for now and then: it can still roll while it burns. </summary>
	private void UpdateGround( ThermiteGrenade grenade )
	{
		if ( _hasGround && _sinceGroundCheck < 0.5f ) return;
		_sinceGroundCheck = 0;

		var tr = Scene.Trace.Ray( grenade.WorldPosition + Vector3.Up * 6f, grenade.WorldPosition + Vector3.Down * 24f )
			.IgnoreGameObjectHierarchy( grenade.GameObject )
			.IgnoreDynamic()
			.WithoutTags( "player", "trigger", "playerclip", "ragdoll", "corpse", "grenade", "particles", "movement", "clutter" )
			.Run();

		_hasGround = tr.Hit && !tr.StartedSolid;
		if ( _hasGround ) _ground = tr.HitPosition;
	}

	private Vector3 PoolCentre( Vector3 top ) => _hasGround ? _ground : top;

	/// <summary>
	/// The slag pool: it spreads as molten iron runs out of the canister, glows at the burn's heat while it's fed, then
	/// cools, and fades once it's too cool to glow.
	/// </summary>
	private void UpdatePool( float t, float intensity )
	{
		if ( !_hasGround )
		{
			_pool.Color = Color.Black;
			return;
		}

		var kelvin = t <= ThermiteGrenade.BurnTime
			? PoolKelvin
			: 300f + (PoolKelvin - 300f) * MathF.Exp( -(t - ThermiteGrenade.BurnTime) / PoolCooling );
		var grown = Math.Clamp( t / ThermiteGrenade.BurnTime, 0f, 1f );
		var size = 8f + 6f * MathF.Sqrt( grown );

		_pool.WorldPosition = _ground + Vector3.Up * 0.4f;
		_pool.WorldRotation = Rotation.LookAt( Vector3.Up );
		_pool.Size = new Vector2( size, size );

		var fade = Math.Clamp( (kelvin - GlowKelvin) / 200f, 0f, 1f );
		var fed = t < 0.5f ? t / 0.5f : 1f;
		_pool.Color = FireParticles.Incandescence( kelvin, 6f ) * (fade * fed * (0.85f + 0.15f * MathF.Max( intensity, 0.3f )));
	}

	private void UpdateLight( Vector3 top, Vector3 axis, float t, float glare )
	{
		if ( !_light.IsValid() ) return;

		// About 2,500 K: the colour the burn lights things with, though the burn itself looks white.
		var lit = new Color( 1f, 0.62f, 0.27f );
		var brightness = 12f * glare;
		var radius = 700f + 200f * glare;

		// After the burn, the slag's dull glow lights only the ground round it.
		if ( glare <= 0f && t > ThermiteGrenade.BurnTime )
		{
			var kelvin = 300f + (PoolKelvin - 300f) * MathF.Exp( -(t - ThermiteGrenade.BurnTime) / PoolCooling );
			var glow = Math.Clamp( (kelvin - GlowKelvin) / 1200f, 0f, 1f );
			lit = FireParticles.Incandescence( kelvin, 1f );
			var peak = MathF.Max( lit.r, 0.001f );
			lit = new Color( lit.r / peak, lit.g / peak, lit.b / peak );
			brightness = 0.6f * glow * glow;
			radius = 80f + 20f * glow;
		}

		_light.Enabled = brightness > 0.005f;
		if ( !_light.Enabled ) return;

		// Just above the burning top, off the canister, so the canister doesn't shade its own light.
		_light.WorldPosition = glare > 0f ? top + axis * 2f + Vector3.Up * 6f : PoolCentre( top ) + Vector3.Up * 4f;
		_light.Radius = radius;
		_light.LightColor = lit * brightness;
	}

	private void UpdateSound( Vector3 top, float intensity )
	{
		if ( intensity > 0f && !_ignitePlayed )
		{
			_ignitePlayed = true;
			Sound.Play( IgniteSound, top );
		}

		if ( intensity > 0f )
		{
			if ( _loop is null || !_loop.IsValid || _loop.IsStopped )
				_loop = Sound.Play( BurnSound, top );

			if ( _loop is not null && _loop.IsValid )
			{
				_loop.Position = top;
				_loop.Volume = MathF.Min( 1f, intensity * 1.1f );
			}

			return;
		}

		if ( _loop is not null && _loop.IsValid && !_loop.IsStopped )
			_loop.Stop( 1.5f );
		_loop = null;
	}

	private Vector3 SampleWind( Vector3 at )
	{
		if ( !_wind.IsValid() ) _wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		return _wind.IsValid() && _wind.Active ? _wind.Sample( at ) : Vector3.Zero;
	}

	/// <summary> Out of the vents, up and along the canister, in a wide cone. </summary>
	private static Vector3 VentDirection( Vector3 axis, float spread )
	{
		var aim = (axis * 0.6f + Vector3.Up * 0.4f).Normal;
		var direction = (aim + Vector3.Random * spread).Normal;
		return direction.z < -0.2f ? direction.WithZ( -direction.z ) : direction;
	}

	private void EmitSpark( Vector3 top, Vector3 axis )
	{
		var random = Random.Shared;
		var velocity = VentDirection( axis, 0.9f ) * random.Float( SparkSpeedMin, SparkSpeedMax );

		// Burning bits of metal, white-hot as they leave, cooling in a fraction of a second.
		SparkParticles.Emit( _sparks, top, velocity, random.Float( 0.6f, 1.2f ), random.Float( 2200f, 2600f ),
			random.Float( 0.25f, 0.6f ), Gravity, random.Float( 0.3f, 1f ), brightness: 10f );
	}

	private void EmitDrop( Vector3 top, Vector3 axis )
	{
		var random = Random.Shared;
		var velocity = VentDirection( axis, 1.2f ) * random.Float( 40f, 150f );

		// Molten iron: heavy, barely slowed by the air, glowing for seconds where it lands.
		SparkParticles.Emit( _drops, top, velocity, random.Float( 1.5f, 2.5f ), random.Float( 2000f, 2300f ),
			random.Float( 1.5f, 4f ), Gravity, random.Float( 0.1f, 0.2f ), brightness: 6f );
	}

	private void EmitFlame( Vector3 top, float intensity )
	{
		var random = Random.Shared;
		var tall = random.Float( 18f, 30f ) * intensity;
		var wide = random.Float( 6f, 10f );

		// The sheet's own orange, pushed towards white by the heat.
		FlameParticles.Emit( _flames, top, wide, tall, random.Float( 0.2f, 0.4f ), new Color( 2.5f, 2.1f, 1.5f, 1f ) );
	}

	private void EmitSmoke( Vector3 at, float strength )
	{
		var random = Random.Shared;
		var shade = random.Float( 0.78f, 0.86f );

		// Thick white smoke: aluminium and barium oxides, as fine as flour.
		FireSmokeParticles.Emit( _smoke, at + Vector3.Up * 6f, random.Float( 10f, 16f ) * strength + 4f,
			random.Float( 90f, 160f ) * (0.4f + 0.6f * strength), random.Float( 120f, 220f ) * strength + 20f,
			random.Float( 5f, 9f ), new Color( shade, shade, shade * 0.97f, 0.55f * strength + 0.15f ) );
	}
}
