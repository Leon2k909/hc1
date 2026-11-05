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

	/// <summary> Emission rate for open fires. Contained fires use continuous sources attached to their fuel. </summary>
	[Property] public float FlamesPerSecond { get; set; } = 16f;

	/// <summary> Inner radius of a drum or brazier opening; 0 leaves an open fire unrestricted. </summary>
	[Property] public float OpeningRadius { get; set; }

	/// <summary> Height of the rim above this emitter's fuel bed. </summary>
	[Property] public float OpeningHeight { get; set; }

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
	private bool _containedVisuals;
	private const int VisualVersion = 2;
	private int _visualVersion;

	protected override void OnEnabled()
	{
		if ( Application.IsDedicatedServer || _visuals.IsValid() ) return;
		_seed = Random.Shared.Float( 0f, 100f );

		_visuals = new GameObject( GameObject, true, "Fire Visuals" );
		_visuals.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked | GameObjectFlags.Hidden;
		_visuals.NetworkMode = NetworkMode.Never;

		_containedVisuals = OpeningRadius > 0f;
		_visualVersion = VisualVersion;
		_flames = _containedVisuals
			? FireParticles.Create<BarrelFlameParticles>( _visuals, "Fuel Flames", FireParticles.Flame, 16,
				additive: true, upright: true, feather: 2f )
			: FireParticles.Create<FlameParticles>( _visuals, "Flames", FireParticles.Flame, 160,
				additive: true, upright: true, feather: 8f );
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
		// Rebuild if hotload or an editor property change switches between open and contained fire.
		if ( _visuals.IsValid() && (_visualVersion != VisualVersion || _containedVisuals != (OpeningRadius > 0f)) )
		{
			OnDisabled();
			OnEnabled();
		}
		if ( !_flames.IsValid() ) return;

		var dt = Time.Delta;
		var at = WorldPosition;
		var camera = Scene.Camera.IsValid() ? Scene.Camera.WorldPosition : at;
		var distance = at.Distance( camera );
		var detail = distance < DetailDistance ? 1f : MathF.Max( 0.2f, DetailDistance / distance );

		var wind = SampleWind( at );
		var contained = OpeningRadius > 0f;
		var fireTime = Time.Now + _seed;
		var burn = contained ? Math.Clamp( 0.82f + 0.16f * MathF.Sin( fireTime * 1.7f )
			+ 0.1f * MathF.Sin( fireTime * 4.1f + 0.7f ), 0.55f, 1.08f ) : 1f;
		if ( contained )
		{
			_flames.GetComponent<BarrelFlameParticles>().UpdateFuel( at, OpeningRadius, OpeningHeight, FlameHeight, burn );
		}
		else
			_flames.GetComponent<FlameParticles>().Wind = wind;
		if ( _smoke.IsValid() ) _smoke.GetComponent<FireSmokeParticles>().Wind = wind;
		if ( _embers.IsValid() ) _embers.GetComponent<SparkParticles>().Wind = wind;

		var random = Random.Shared;
		_flameDebt += contained ? 0f : FlamesPerSecond * detail * dt;
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
				if ( contained ) p.z = at.z + OpeningHeight + FlameHeight * 0.25f;
				var shade = SmokeShade * random.Float( 0.85f, 1.15f );
				FireSmokeParticles.Emit( _smoke, p, SmokeSize * random.Float( 0.2f, 0.3f ), SmokeSize * random.Float( 0.8f, 1.3f ),
					contained ? random.Float( 30f, 55f ) : random.Float( 60f, 110f ), SmokeLife * random.Float( 0.8f, 1.2f ),
					new Color( shade, shade * 0.96f, shade * 0.92f, contained ? 0.2f : 0.6f ) );
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
				if ( contained )
				{
					p.z = at.z + OpeningHeight + random.Float( 0f, FlameHeight * 0.3f );
					velocity = new Vector3( random.Float( -10f, 10f ), random.Float( -10f, 10f ), random.Float( 40f, 85f ) );
				}
				SparkParticles.Emit( _embers, p, velocity, contained ? random.Float( 0.3f, 0.65f ) : random.Float( 0.7f, 1.4f ), random.Float( 1150f, 1350f ),
					contained ? random.Float( 1f, 1.5f ) : random.Float( 1.0f, 2.2f ), gravity: contained ? 16f : 60f,
					drag: contained ? 1.8f : 1.5f, brightness: contained ? 4f : 8f );
			}
		}

		if ( _light.IsValid() )
		{
			var t = Time.Now + _seed;
			var flicker = 0.78f + 0.12f * MathF.Sin( t * 13.1f ) + 0.07f * MathF.Sin( t * 29.3f + 1.3f ) + 0.05f * MathF.Sin( t * 5.7f + 0.4f );
			if ( contained )
			{
				flicker = (0.86f + 0.08f * MathF.Sin( t * 5.3f ) + 0.06f * MathF.Sin( t * 2.1f + 0.7f )
					+ 0.03f * MathF.Sin( t * 13.1f )) * (0.8f + 0.2f * burn);
				var lightPosition = Vector3.Up * (OpeningHeight + FlameHeight * 0.2f);
				if ( _light.LocalPosition != lightPosition ) _light.LocalPosition = lightPosition;
			}
			_light.LightColor = new Color( 1f, 0.55f, 0.22f ) * (LightBrightness * flicker);
		}
	}

	private Vector3 SampleWind( Vector3 at )
	{
		if ( !_wind.IsValid() ) _wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		return _wind.IsValid() && _wind.Active ? _wind.Sample( at ) : Vector3.Zero;
	}
}
