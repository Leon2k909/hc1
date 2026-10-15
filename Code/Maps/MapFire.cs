namespace Facepunch;

/// <summary>
/// A fire that's part of a map's dressing: rubbish burning in an oil drum, a wrecked trailer alight, a far-off blaze
/// with its smoke column. Each machine draws its own flames, smoke and embers with the fire grenade's particles
/// (<see cref="FireParticles"/>) and flickers its own light; nothing is networked, and it neither spreads nor hurts.
/// Riverside places them (Tools/riverside_map.py). The object sits where the flames' base is. It burns in the editor
/// too, so the scene view and offscreen captures show it.
/// </summary>
public sealed class MapFire : Component, Component.ExecuteInEditor
{
	/// <summary> Across the fuel's top, the spread of the flames' bases. </summary>
	[Property] public float Width { get; set; } = 18f;

	/// <summary> How tall its flames reach. </summary>
	[Property] public float FlameHeight { get; set; } = 30f;

	[Property] public float FlamesPerSecond { get; set; } = 16f;

	/// <summary> Smoke puffs a second; 0 for none. A drum's rubbish smokes a little, a burning trailer a column. </summary>
	[Property] public float SmokePerSecond { get; set; } = 2f;

	/// <summary> How big a puff grows, and how long it lives: a column's are big and slow. </summary>
	[Property] public float SmokeSize { get; set; } = 120f;
	[Property] public float SmokeLife { get; set; } = 7f;

	/// <summary> How dark the smoke is (0 black, 1 white). Burning plastic and timber smoke dark. </summary>
	[Property] public float SmokeShade { get; set; } = 0.22f;

	[Property] public float EmbersPerSecond { get; set; } = 5f;

	/// <summary> The firelight's reach; 0 for no light. </summary>
	[Property] public float LightRadius { get; set; } = 380f;
	[Property] public float LightBrightness { get; set; } = 2.4f;
	[Property] public bool LightShadows { get; set; }

	/// <summary> Past this far from the camera only every few flames is drawn, bigger. </summary>
	[Property] public float DetailDistance { get; set; } = 2500f;

	private GameObject _visuals;
	private ParticleEffect _flames, _smoke, _embers;
	private PointLight _light;
	private WorldWind _wind;
	private float _flameDebt, _smokeDebt, _emberDebt, _seed;

	protected override void OnEnabled()
	{
		if ( Application.IsDedicatedServer || _visuals.IsValid() ) return;
		_seed = Random.Shared.Float( 0f, 100f );

		_visuals = new GameObject( GameObject, true, "Fire Visuals" );
		_visuals.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked | GameObjectFlags.Hidden;
		_visuals.NetworkMode = NetworkMode.Never;

		_flames = FireParticles.Create<FlameParticles>( _visuals, "Flames", FireParticles.Flame, 160, additive: true, upright: true, feather: 8f );
		if ( SmokePerSecond > 0f )
			_smoke = FireParticles.Create<FireSmokeParticles>( _visuals, "Smoke", FireParticles.Smoke, Math.Clamp( (int)(SmokePerSecond * SmokeLife * 1.5f), 8, 200 ),
				additive: false, lit: true, sorted: true, feather: 24f );
		if ( EmbersPerSecond > 0f )
			_embers = FireParticles.Create<SparkParticles>( _visuals, "Embers", FireParticles.Ember, 80, additive: true, feather: 0f );

		if ( LightRadius > 0f )
		{
			var go = new GameObject( _visuals, true, "Firelight" );
			go.LocalPosition = Vector3.Up * (FlameHeight * 0.6f + 8f);
			_light = go.AddComponent<PointLight>();
			_light.Radius = LightRadius;
			_light.Shadows = LightShadows;
			_light.Attenuation = 1f;
			_light.LightColor = new Color( 1f, 0.55f, 0.22f ) * LightBrightness;
		}
	}

	protected override void OnDisabled()
	{
		if ( _visuals.IsValid() ) _visuals.Destroy();
		_visuals = null;
	}

	protected override void OnUpdate()
	{
		if ( !_flames.IsValid() ) return;

		var dt = Time.Delta;
		var at = WorldPosition;
		var camera = Scene.Camera.IsValid() ? Scene.Camera.WorldPosition : at;
		var distance = at.Distance( camera );
		var detail = distance < DetailDistance ? 1f : MathF.Max( 0.2f, DetailDistance / distance );

		var wind = SampleWind( at );
		_flames.GetComponent<FlameParticles>().Wind = wind;
		if ( _smoke.IsValid() ) _smoke.GetComponent<FireSmokeParticles>().Wind = wind;
		if ( _embers.IsValid() ) _embers.GetComponent<SparkParticles>().Wind = wind;

		var random = Random.Shared;
		_flameDebt += FlamesPerSecond * detail * dt;
		while ( _flameDebt >= 1f )
		{
			_flameDebt -= 1f;
			var tall = FlameHeight * random.Float( 0.55f, 1.1f ) / MathF.Sqrt( detail );
			var wide = MathF.Max( tall / FireParticles.FlameAspect * 1.1f, Width * 0.35f );
			var spot = at + new Vector3( random.Float( -0.5f, 0.5f ) * Width, random.Float( -0.5f, 0.5f ) * Width, 0f );
			var life = random.Float( 0.4f, 0.75f ) * MathF.Sqrt( MathF.Max( tall, 10f ) / 40f );
			FlameParticles.Emit( _flames, spot, wide, tall, life, new Color( 1.4f, 1.2f, 1.05f, 1f ) );
		}

		if ( _smoke.IsValid() )
		{
			_smokeDebt += SmokePerSecond * dt;
			while ( _smokeDebt >= 1f )
			{
				_smokeDebt -= 1f;
				var p = at + new Vector3( random.Float( -0.4f, 0.4f ) * Width, random.Float( -0.4f, 0.4f ) * Width, FlameHeight * 0.85f );
				var shade = SmokeShade * random.Float( 0.85f, 1.15f );
				FireSmokeParticles.Emit( _smoke, p, SmokeSize * random.Float( 0.2f, 0.3f ), SmokeSize * random.Float( 0.8f, 1.3f ),
					random.Float( 60f, 110f ), SmokeLife * random.Float( 0.8f, 1.2f ), new Color( shade, shade * 0.96f, shade * 0.92f, 0.6f ) );
			}
		}

		if ( _embers.IsValid() )
		{
			_emberDebt += EmbersPerSecond * detail * dt;
			while ( _emberDebt >= 1f )
			{
				_emberDebt -= 1f;
				var p = at + new Vector3( random.Float( -0.4f, 0.4f ) * Width, random.Float( -0.4f, 0.4f ) * Width, FlameHeight * random.Float( 0.3f, 0.9f ) );
				var velocity = new Vector3( random.Float( -25f, 25f ), random.Float( -25f, 25f ), random.Float( 80f, 180f ) );
				SparkParticles.Emit( _embers, p, velocity, random.Float( 0.7f, 1.4f ), random.Float( 1150f, 1350f ),
					random.Float( 1.0f, 2.2f ), gravity: 60f, drag: 1.5f, brightness: 8f );
			}
		}

		if ( _light.IsValid() )
		{
			var t = Time.Now + _seed;
			var flicker = 0.78f + 0.12f * MathF.Sin( t * 13.1f ) + 0.07f * MathF.Sin( t * 29.3f + 1.3f ) + 0.05f * MathF.Sin( t * 5.7f + 0.4f );
			_light.LightColor = new Color( 1f, 0.55f, 0.22f ) * (LightBrightness * flicker);
		}
	}

	private Vector3 SampleWind( Vector3 at )
	{
		if ( !_wind.IsValid() ) _wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		return _wind.IsValid() && _wind.Active ? _wind.Sample( at ) : Vector3.Zero;
	}
}
