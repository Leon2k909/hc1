namespace Facepunch;

/// <summary>
/// Particle effects built in code for fire (<see cref="SurfaceFire"/>, <see cref="ThermiteBurnEffect"/>), from the
/// engine's own flame, smoke, spark and glow sheets. The effects emit nothing themselves: the fire emits each particle,
/// and a controller gives it its own life (<see cref="FlameParticles"/>, <see cref="FireSmokeParticles"/>,
/// <see cref="SparkParticles"/>).
/// </summary>
public static class FireParticles
{
	public const string Flame = "textures/particles/flame/flame_01_side.vtex";
	public const string Smoke = "textures/particles/smoke/smoke_loop_c.vtex";
	public const string Spark = "textures/particles/spark_white.vtex";
	public const string Glow = "textures/particles/glow_simple_01.vtex";
	public const string Ember = "textures/particles/flame/ember.vtex";

	/// <summary> The flame sheet's frames are 122 by 160. </summary>
	public const float FlameAspect = 160f / 122f;

	/// <summary> Longer than any particle lives: the controllers end each one's life themselves. </summary>
	private const float EffectLifetime = 600f;

	private static readonly Dictionary<string, Sprite> Sprites = new();

	public static Sprite SpriteOf( string texture )
	{
		if ( Sprites.TryGetValue( texture, out var sprite ) ) return sprite;
		sprite = Sprite.FromTexture( Texture.Load( texture ) );
		Sprites[texture] = sprite;
		return sprite;
	}

	/// <summary> A particle effect under <paramref name="parent"/> that only this machine has. </summary>
	public static ParticleEffect Create<T>( GameObject parent, string name, string texture, int maxParticles,
		bool additive, bool lit = false, bool sorted = false, bool upright = false, float feather = 8f )
		where T : ParticleController, new()
	{
		var go = new GameObject( parent, true, name );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.Tags.Add( "particles" );

		var effect = go.AddComponent<ParticleEffect>();
		effect.MaxParticles = maxParticles;
		effect.Lifetime = EffectLifetime;
		effect.LocalSpace = 0f;

		var renderer = go.AddComponent<ParticleSpriteRenderer>();
		renderer.Sprite = SpriteOf( texture );
		renderer.Additive = additive;
		renderer.Lighting = lit;
		renderer.Shadows = false;
		renderer.DepthFeather = feather;
		renderer.SortMode = sorted
			? ParticleSpriteRenderer.ParticleSortMode.ByDistance
			: ParticleSpriteRenderer.ParticleSortMode.Unsorted;
		renderer.Alignment = upright
			? ParticleSpriteRenderer.BillboardAlignment.RotateToCamera
			: ParticleSpriteRenderer.BillboardAlignment.LookAtCamera;

		go.AddComponent<T>();
		return effect;
	}

	/// <summary>
	/// Roughly the colour a body glows at <paramref name="kelvin"/> (Tanner Helland's fit), and how bright against one
	/// at thermite's 2,500 K, which goes as the fourth power of the temperature.
	/// </summary>
	public static Color Incandescence( float kelvin, float brightnessAt2500 )
	{
		var t = kelvin / 100f;
		var g = Math.Clamp( 99.47f * MathF.Log( t ) - 161.12f, 0f, 255f ) / 255f;
		var b = t <= 19f ? 0f : Math.Clamp( 138.52f * MathF.Log( t - 10f ) - 305.04f, 0f, 255f ) / 255f;
		var brightness = brightnessAt2500 * MathF.Pow( kelvin / 2500f, 4f );
		return new Color( brightness, g * brightness, b * brightness, 1f );
	}
}

/// <summary>
/// Flames: each one rises, grows, flickers through the flame sheet and dies down over its own life. Emit with
/// <see cref="Emit"/>.
/// </summary>
[Hide]
public sealed class FlameParticles : ParticleController
{
	/// <summary> The wind (units/s), which leans the flames and carries them. Set from the main thread. </summary>
	public Vector3 Wind { get; set; }

	/// <summary> The flame sheet plays at this many frames a second, of its 64. </summary>
	private const float FramesPerSecond = 30f;

	/// <summary> A flame lasting <paramref name="life"/> seconds, <paramref name="width"/> by <paramref name="height"/> units at its fullest. </summary>
	public static void Emit( ParticleEffect effect, Vector3 groundAt, float width, float height, float life, Color tint )
	{
		if ( !effect.IsValid() || effect.IsFull ) return;

		var p = effect.Emit( groundAt + Vector3.Up * (height * 0.25f), Random.Shared.Float() );
		// Spare fields, since the effect doesn't use them: life, and the full size and the ground's height.
		p.StartScale = life;
		p.HitNormal = new Vector3( width, height, groundAt.z );
		p.Color = tint;
		p.Alpha = 0f;
		p.Size = new Vector3( width * 0.5f, height * 0.5f, 1f );
		p.SequenceTime = new Vector3( 0f, 0f, Random.Shared.Float() );
		p.Angles = new Angles( 0f, 0f, Random.Shared.Float( -6f, 6f ) );
		p.Velocity = Vector3.Zero;
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

		// Full size a quarter of the way through, then a little smaller as it burns out.
		var full = p.HitNormal;
		var grow = t < 0.25f ? 0.5f + 2f * t : 1f - 0.3f * (t - 0.25f) / 0.75f;
		p.Size = new Vector3( full.x * grow, full.y * grow, 1f );
		p.Alpha = t < 0.12f ? t / 0.12f : t > 0.55f ? (1f - t) / 0.45f : 1f;
		p.SequenceTime.y = p.Age * FramesPerSecond / 64f;

		// Its base stays in the fuel while the tongue grows, then it lifts off; the wind carries it along.
		var rise = t < 0.5f ? 0f : full.y * 0.9f * (t - 0.5f);
		p.Position.z = full.z + p.Size.y * 0.45f + rise;
		p.Velocity = Wind.WithZ( 0f ) * 0.5f;
	}
}

/// <summary>
/// Smoke: buoyant while it's hot, then carried by the wind, spreading and thinning as it goes. Emit with
/// <see cref="Emit"/>.
/// </summary>
[Hide]
public sealed class FireSmokeParticles : ParticleController
{
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
	/// A puff lasting <paramref name="life"/> seconds that grows from <paramref name="startSize"/> to
	/// <paramref name="endSize"/> units, rising at up to <paramref name="lift"/> units/s while it's hot.
	/// </summary>
	public static void Emit( ParticleEffect effect, Vector3 at, float startSize, float endSize, float lift, float life,
		Color color )
	{
		if ( !effect.IsValid() || effect.IsFull ) return;

		var p = effect.Emit( at, Random.Shared.Float() );
		p.StartScale = life;
		p.HitNormal = new Vector3( startSize, endSize, lift );
		p.HitPos = new Vector3( Random.Shared.Float( -12f, 12f ), Random.Shared.Float( 0f, 100f ), 0f );
		p.Color = color;
		p.Alpha = 0f;
		p.Size = startSize;
		p.SequenceTime = new Vector3( 0f, 0f, Random.Shared.Float() );
		p.Angles = new Angles( 0f, 0f, Random.Shared.Float( 0f, 360f ) );
		p.Velocity = Vector3.Up * lift;
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
		p.Size = MathX.Lerp( shape.x, shape.y, 1f - (1f - t) * (1f - t) );
		p.Alpha = t < 0.1f ? t / 0.1f : t > 0.5f ? (1f - t) / 0.5f : 1f;
		p.Angles.roll += p.HitPos.x * _dt;
		p.SequenceTime.y = p.Age * 8f / 64f;

		// Hot smoke rises and slows as it cools; the eddies are a smooth field, so puffs near each other roll together.
		var seed = p.HitPos.y;
		var q = p.Position / 90f;
		var eddy = new Vector3(
			MathF.Sin( q.z + _time * 0.5f + seed ) + MathF.Cos( q.y - _time * 0.4f ),
			MathF.Sin( q.x + _time * 0.45f + seed ) + MathF.Cos( q.z + _time * 0.35f ),
			MathF.Sin( q.y - _time * 0.3f + seed ) * 0.5f ) * 10f;
		var target = Wind + Vector3.Up * (shape.z * MathF.Exp( -p.Age / 4f )) + eddy;
		p.Velocity += (target - p.Velocity) * (1f - MathF.Exp( -_dt * 1.2f ));
	}
}

/// <summary>
/// Sparks and embers: glowing bits that cool as they fly, drop under gravity or float up with the heat, and fade as
/// they drop below a visible glow. Emit with <see cref="Emit"/>.
/// </summary>
[Hide]
public sealed class SparkParticles : ParticleController
{
	/// <summary> The wind (units/s), which carries the light ones. Set from the main thread. </summary>
	public Vector3 Wind { get; set; }

	/// <summary> A spark this much cooler than its start has stopped glowing enough to see. </summary>
	private const float VisibleKelvin = 900f;

	private float _dt;

	protected override void OnBeforeStep( float delta ) => _dt = delta;

	/// <summary>
	/// A spark starting at <paramref name="kelvin"/> that cools with the time constant <paramref name="cooling"/>
	/// seconds, falls with <paramref name="gravity"/> (units/s², negative floats up) and is slowed by
	/// <paramref name="drag"/> (1/s).
	/// </summary>
	public static void Emit( ParticleEffect effect, Vector3 at, Vector3 velocity, float size, float kelvin, float cooling,
		float gravity, float drag, float brightness )
	{
		if ( !effect.IsValid() || effect.IsFull ) return;

		var p = effect.Emit( at, Random.Shared.Float() );
		// The effect collides, which uses HitPos and HitNormal, so these go in StartAngles and StartPosition.
		p.StartScale = size;
		p.StartAngles = new Angles( kelvin, cooling, drag );
		p.StartPosition = new Vector3( gravity, brightness, 0f );
		p.Velocity = velocity;
		p.Size = size;
		p.Color = FireParticles.Incandescence( kelvin, brightness );
		p.Alpha = 1f;
	}

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var start = p.StartAngles;
		var kelvin = 300f + (start.pitch - 300f) * MathF.Exp( -p.Age / MathF.Max( start.yaw, 0.01f ) );
		if ( kelvin < VisibleKelvin )
		{
			p.Alpha = 0f;
			p.Age = 1e6f;
			return;
		}

		var physics = p.StartPosition;
		p.Color = FireParticles.Incandescence( kelvin, physics.y );
		p.Alpha = Math.Clamp( (kelvin - VisibleKelvin) / 150f, 0f, 1f );
		p.Size = p.StartScale * (0.6f + 0.4f * Math.Clamp( (kelvin - VisibleKelvin) / 1000f, 0f, 1f ));

		var air = start.roll > 0f ? Wind - p.Velocity : Vector3.Zero;
		p.Velocity += (air * start.roll + Vector3.Down * physics.x) * _dt;
	}
}
