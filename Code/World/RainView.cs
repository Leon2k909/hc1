namespace Facepunch;

/// <summary>
/// The rain as one machine sees and hears it, round its own camera: the drops (<see cref="RainDropParticles"/>), their
/// splashes on open ground (<see cref="RainSplashParticles"/>), the puddles (<see cref="RainPuddles"/>) and the rings
/// the drops make on them (<see cref="RainRippleParticles"/>), the rain's sound, the overcast look of the sky, sun and fog (<see cref="RainLook"/>), and the lightning's flashes and thunder
/// (<see cref="Weather.Schedule.Strikes"/>). Made by <see cref="Weather"/> while it rains, and it goes once the weather
/// has cleared and the look has eased back. Nothing here is networked.
/// </summary>
public sealed class RainView : Component
{
	public Weather Weather { get; set; }

	/// <summary> The most drops in the air round the camera; how many show goes by the rate (<see cref="ActiveShare"/>). </summary>
	public const int MaxDrops = 10000;
	public const int MaxSplashes = 3000;
	public const int MaxRipples = 3000;

	/// <summary> Square units in a square metre. </summary>
	private const float SquareUnitsPerSquareMetre = WorldWind.UnitsPerMetre * WorldWind.UnitsPerMetre;

	/// <summary> How long the sky, sun and fog take to come in or go back (seconds). </summary>
	private const float LookTime = 20f;

	private const string LightLoop = "sounds/weather/rain_light.sound";
	private const string HeavyLoop = "sounds/weather/rain_heavy.sound";
	private const string RoofLoop = "sounds/weather/rain_roof.sound";

	/// <summary>
	/// The drops' layers round the camera: radius, share of the drops, and how strongly each of its drops is drawn. Most
	/// are close, where they show. The outer layers hold 10 and 70 times fewer drops to the cubic unit than the inner
	/// one, so each of their drops stands for a few of the many there, short of all of them: past 15-20 m nobody makes
	/// out single drops, and the fog does the rest. At 2.5 and 5.6 the far drops read as bright threads.
	/// </summary>
	private static readonly (float Radius, float Share, float Weight)[] Layers =
		{ (220f, 0.45f, 1f), (520f, 0.35f, 1.6f), (900f, 0.2f, 2.4f) };

	private readonly ShelterGrid _grid = new();
	private readonly RainLook _look = new();
	private readonly RainPuddles _puddles = new();
	private ParticleEffect _drops;
	private ParticleEffect _splashes;
	private ParticleEffect _ripples;
	private RainDropParticles _dropController;
	private RainSplashParticles _splashController;
	private RainRippleParticles _rippleController;
	private float _splashCarry, _rippleCarry;
	private WorldWind _wind;

	/// <summary> How far the overcast look has come in, 0-1. </summary>
	private float _k;

	private SoundHandle _light, _heavy, _roof;
	private float _lightBase, _heavyBase, _roofBase;
	private float _outdoorGain = 1f, _underGain;

	protected override void OnStart() => EnsureEffects();

	/// <summary> Makes any of the three effects that's missing, as after a hotload into a rain made before it. </summary>
	private void EnsureEffects()
	{
		if ( !_drops.IsValid() )
		{
			_drops = CreateEffect<RainDropParticles>( "Rain Drops", DropSprite, MaxDrops, 100000f, faceVelocity: true,
				ParticleSpriteRenderer.BillboardAlignment.LookAtCamera, Sandbox.Rendering.FilterMode.Trilinear );
			_dropController = _drops.GetComponent<RainDropParticles>();
		}

		// Splashes and rings live one second of their own age, which each one's TimeScale fits to its life.
		if ( !_splashes.IsValid() )
		{
			_splashes = CreateEffect<RainSplashParticles>( "Rain Splashes", SplashSprite, MaxSplashes, 1f, faceVelocity: false,
				ParticleSpriteRenderer.BillboardAlignment.RotateToCamera, Sandbox.Rendering.FilterMode.Trilinear );
			_splashController = _splashes.GetComponent<RainSplashParticles>();
		}

		if ( !_ripples.IsValid() )
		{
			_ripples = CreateEffect<RainRippleParticles>( "Rain Ripples", RippleSprite, MaxRipples, 1f, faceVelocity: false,
				ParticleSpriteRenderer.BillboardAlignment.Particle, Sandbox.Rendering.FilterMode.Anisotropic );
			_rippleController = _ripples.GetComponent<RainRippleParticles>();
		}
	}

	protected override void OnDisabled()
	{
		_look.Restore();
		_puddles.Dispose();
		StopSounds( 0.5f );
	}

	protected override void OnDestroy()
	{
		_look.Restore();
		_puddles.Dispose();
		StopSounds( 0.5f );
	}

	protected override void OnUpdate()
	{
		var raining = Weather.IsValid() && Weather.IsRaining;
		var rate = raining ? Weather.RainRate : 0f;

		_k = Math.Clamp( _k + (raining ? 1f : -1f) * Time.Delta / LookTime, 0f, 1f );
		if ( !raining && _k <= 0f )
		{
			_look.Restore();
			_puddles.Dispose();
			StopSounds( 1f );
			GameObject.Destroy();
			return;
		}

		var look = SmoothStep( 0f, 1f, _k );
		var darkening = MathX.Lerp( 1f, 0.62f, SmoothStep( 1f, 30f, rate ) * look );

		var camera = Scene.Camera;
		var eye = camera.IsValid() ? camera.WorldPosition : WorldPosition;
		// Indoors the flash comes in through the windows and doors, so it shows less.
		var flash = UpdateLightning( eye ) * look * (0.25f + 0.75f * _outdoorGain);
		_look.Apply( Scene, look, rate, flash );

		if ( !camera.IsValid() ) return;
		WorldPosition = eye;
		EnsureEffects();

		_grid.Update( Scene, eye );
		_puddles.Update( Scene, Weather, _grid, eye, look );

		// The rain comes in with the cloud, over the first few seconds of the look.
		var opacity = SmoothStep( 0f, 0.2f, rate ) * Math.Clamp( _k / 0.3f, 0f, 1f );

		UpdateDrops( camera, eye, rate, opacity, darkening, flash );
		UpdateSplashes( camera, eye, rate, opacity, darkening, flash );
		UpdateRipples( camera, eye, rate, opacity, darkening, flash );
		UpdateSound( eye, rate, opacity );
	}

	// ── Drops ───────────────────────────────────────────────────────────────────

	/// <summary>
	/// The share of the drops that show at a rate (mm/h): more drops in the air the harder it rains, from a few hundred
	/// in drizzle to all of them in a downpour (800 at 1 mm/h, 2,100 at 5 and 5,500 at 25).
	/// </summary>
	public static float ActiveShare( float rate ) => Math.Clamp( 800f * MathF.Pow( MathF.Max( rate, 0f ), 0.6f ), 250f, MaxDrops ) / MaxDrops;

	/// <summary> Marshall and Palmer's drop sizes: the slope of the exponential spread (per mm) at a rate (mm/h). </summary>
	public static float MarshallPalmerLambda( float rate ) => 4.1f * MathF.Pow( MathF.Max( rate, 0.05f ), -0.21f );

	/// <summary>
	/// The rain's haze (linear): the overcast horizon of <c>Tools/rain_sky.py</c>'s sky, which the fog takes, lit by any
	/// lightning as the fog is. Drops, splashes and rings are water, which shows what's round it, so each is drawn in a
	/// share of it: never white, and never brighter than the sky it refracts.
	/// </summary>
	private static Color Haze( float darkening, float flash ) =>
		RainLook.Lit( new Color( 0.224f * darkening, 0.231f * darkening, 0.244f * darkening, 1f ), 2f * flash );

	/// <summary>
	/// A drop's colour against the haze. It shows the scene behind it upside down through about 165 degrees, half sky
	/// (the horizon to the zenith, 1-1.67 of the horizon) and half wet ground (0.32), plus a few per cent reflected off
	/// its face. So it's a little darker than the sky round it, and brighter than a dark wall behind it.
	/// </summary>
	private const float DropShade = 0.85f;

	/// <summary> A splash's crown, whose sheet of water reflects more of the sky at its grazing angles. </summary>
	private const float SplashShade = 1f;

	/// <summary> A ring's crests, tilted water that reflects sky higher up than the flat puddle does. </summary>
	private const float RippleShade = 1.3f;

	private static Color Shade( Color haze, float share ) => new( haze.r * share, haze.g * share, haze.b * share, 1f );

	private void UpdateDrops( CameraComponent camera, Vector3 eye, float rate, float opacity, float darkening, float flash )
	{
		if ( !_drops.IsValid() || !_dropController.IsValid() ) return;

		// Top the drops up; each keeps its layer and size for life, and wraps round the camera.
		while ( !_drops.IsFull )
		{
			var layer = PickLayer( Random.Shared.NextSingle() );
			var radius = Layers[layer].Radius;
			var position = eye + new Vector3( Random.Shared.Float( -radius, radius ), Random.Shared.Float( -radius, radius ),
				Random.Shared.Float( -250f, 150f + 0.6f * radius ) );
			var p = _drops.Emit( position, Random.Shared.NextSingle() );
			p.StartPosition = new Vector3( Random.Shared.NextSingle(), Random.Shared.NextSingle(), radius );
			p.StartAngles = new Angles( 0f, Layers[layer].Weight, 0f );
			p.Alpha = 0f;
			p.Size = new Vector3( 0.1f, 1f, 1f );
		}

		if ( !_wind.IsValid() ) _wind = Scene.GetAllComponents<WorldWind>().FirstOrDefault();
		var lambda = MarshallPalmerLambda( rate );
		var tint = Shade( Haze( darkening, flash ), DropShade );
		_dropController.Frame = new RainDropParticles.DropFrame(
			Camera: eye,
			Wind: _wind.IsValid() && _wind.Active ? _wind.Velocity * WorldWind.UnitsPerMetre : Vector3.Zero,
			Gust: _wind.IsValid() ? _wind.GustStrength : 0f,
			WindTime: _wind.IsValid() ? _wind.Elapsed : 0f,
			Lambda: lambda,
			LambdaC: 1f - MathF.Exp( -lambda * (RainDropParticles.MaxDiameter - RainDropParticles.MinDiameter) ),
			Active: rate > 0f ? ActiveShare( rate ) : 0f,
			PixelAngle: PixelAngle( camera ),
			Tint: tint,
			Opacity: opacity,
			Grid: _grid );
	}

	private static int PickLayer( float u )
	{
		for ( var i = 0; i < Layers.Length - 1; i++ )
		{
			if ( u < Layers[i].Share ) return i;
			u -= Layers[i].Share;
		}
		return Layers.Length - 1;
	}

	/// <summary> The angle one pixel takes across the screen's width (radians), so far drops stay at least a pixel or two wide. </summary>
	private static float PixelAngle( CameraComponent camera )
	{
		var width = MathF.Max( Screen.Width, 1f );
		var fov = camera.FieldOfView.DegreeToRadian();
		if ( camera.FovAxis == CameraComponent.Axis.Vertical )
			fov = 2f * MathF.Atan( MathF.Tan( fov * 0.5f ) * MathF.Max( Screen.Aspect, 0.1f ) );
		return 2f * MathF.Tan( fov * 0.5f ) / width;
	}

	// ── Splashes ────────────────────────────────────────────────────────────────

	/// <summary> How far out splashes are made: past that, even a thinned-out one is under a pixel. </summary>
	private const float SplashRange = 900f;

	/// <summary> The most splashes made a second, and the most places tried for them in a frame. </summary>
	private const float SplashBudget = 30000f;
	private const int SplashTriesPerFrame = 3000;

	/// <summary> The share of the places tried lately that were open ground in view, so the budget goes on those. </summary>
	private float _splashAccept = 0.3f;
	private int _splashTried, _splashMade;

	/// <summary>
	/// How many drops at least <paramref name="minDiameter"/> mm across land on a square unit each second at a rate
	/// (mm/h): Marshall and Palmer's spread times each size's fall speed, summed. Over a square metre, about 730 drops
	/// over 1 mm land a second at 5 mm/h, 150 at 1 mm/h and 2,500 at 25 mm/h.
	/// </summary>
	public static float DropFlux( float rate, float minDiameter )
	{
		if ( rate <= 0f ) return 0f;
		var lambda = MarshallPalmerLambda( rate );
		var perSquareMetre = 8000f * (9.65f * MathF.Exp( -lambda * minDiameter ) / lambda
			- 10.3f * MathF.Exp( -(lambda + 0.6f) * minDiameter ) / (lambda + 0.6f));
		return MathF.Max( perSquareMetre, 0f ) / SquareUnitsPerSquareMetre;
	}

	/// <summary>
	/// The radius inside which every drop gets its splash, when past it a share (r0 / r)² of them do, out to
	/// <paramref name="range"/>, so that <paramref name="flux"/> comes to <paramref name="budget"/> a second.
	/// </summary>
	private static float CoreRadius( float flux, float budget, float range )
	{
		if ( flux * MathF.PI * range * range <= budget ) return range;
		// The disc's weighted area over 2 pi is r0² (1/2 + ln(range / r0)), which grows with r0.
		var target = budget / (MathF.Tau * flux);
		var low = 0.01f;
		var high = range;
		for ( var i = 0; i < 30; i++ )
		{
			var mid = 0.5f * (low + high);
			if ( mid * mid * (0.5f + MathF.Log( range / mid )) > target ) high = mid;
			else low = mid;
		}
		return low;
	}

	/// <summary> A drop's diameter (mm) from a uniform number, over the exponential spread from <paramref name="from"/> to 5 mm. </summary>
	private static float DiameterFrom( float u, float lambda, float from ) =>
		from - MathF.Log( 1f - u * (1f - MathF.Exp( -lambda * (RainDropParticles.MaxDiameter - from) )) ) / lambda;

	/// <summary> The cosine of the half-angle of a cone round the camera's view that takes in the whole screen, and 3 degrees more. </summary>
	private static float ViewCone( CameraComponent camera )
	{
		var fov = camera.FieldOfView.DegreeToRadian();
		var aspect = MathF.Max( Screen.Aspect, 0.1f );
		float tanH, tanV;
		if ( camera.FovAxis == CameraComponent.Axis.Vertical )
		{
			tanV = MathF.Tan( fov * 0.5f );
			tanH = tanV * aspect;
		}
		else
		{
			tanH = MathF.Tan( fov * 0.5f );
			tanV = tanH / aspect;
		}
		var half = MathF.Atan( MathF.Sqrt( tanH * tanH + tanV * tanV ) ) + 3f.DegreeToRadian();
		return MathF.Cos( MathF.Min( half, MathF.PI ) );
	}

	/// <summary>
	/// A crown for each drop over 1 mm that lands on open, level ground in view: within the core radius every one, past
	/// it a share (r0 / r)², each drawn stronger for the ones it stands for. A crown spreads to 5-9 times its drop's
	/// width and is gone in 25-110 ms.
	/// </summary>
	private void UpdateSplashes( CameraComponent camera, Vector3 eye, float rate, float opacity, float darkening, float flash )
	{
		if ( !_splashes.IsValid() || !_splashController.IsValid() ) return;

		_splashController.Opacity = opacity;
		_splashController.Tint = Shade( Haze( darkening, flash ), SplashShade );

		var flux = DropFlux( rate, 1f ) * opacity;
		if ( flux <= 0f ) return;

		var core = CoreRadius( flux, SplashBudget / _splashAccept, SplashRange );
		var inner = 0.5f * core * core;
		var weighted = core * core * (0.5f + MathF.Log( SplashRange / core ));
		_splashCarry += flux * MathF.Tau * weighted * Time.Delta;
		var tries = (int)_splashCarry;
		_splashCarry -= tries;
		tries = Math.Min( tries, SplashTriesPerFrame );
		if ( tries <= 0 ) return;

		var forward = camera.WorldRotation.Forward;
		var cone = ViewCone( camera );
		var pixel = PixelAngle( camera );
		var lambda = MarshallPalmerLambda( rate );
		var made = 0;

		for ( var i = 0; i < tries && !_splashes.IsFull; i++ )
		{
			// The distance, drawn with the core's weighting: evenly inside it, falling off as (r0 / r)² past it.
			var m = Random.Shared.NextSingle() * weighted;
			var r = m < inner ? MathF.Sqrt( 2f * m ) : core * MathF.Exp( (m - inner) / (core * core) );
			if ( r < 16f ) continue;
			var angle = Random.Shared.NextSingle() * MathF.Tau;
			var at = eye + new Vector3( MathF.Cos( angle ) * r, MathF.Sin( angle ) * r, 0f );
			if ( !_grid.IsFlatOpenGround( at.x, at.y, out var floor ) || floor > eye.z ) continue;

			var to = at.WithZ( floor ) - eye;
			var distance = to.Length;
			if ( Vector3.Dot( to, forward ) < cone * distance ) continue;

			var diameter = DiameterFrom( Random.Shared.NextSingle(), lambda, 1f );
			var crown = Random.Shared.Float( 5f, 9f ) * diameter * 0.03937f;
			// The crown's rim is 0.625 of the sprite's width.
			var sprite = crown * 1.6f;
			var life = (0.025f + 0.012f * diameter) * Random.Shared.Float( 0.7f, 1.3f );
			// Never under a pixel and a half, but fainter by the area it's spread over.
			var minWidth = distance * pixel * 1.5f;
			var share = r <= core ? 1f : (core / r) * (core / r);
			var cover = sprite >= minWidth ? 1f : (sprite / minWidth) * (sprite / minWidth);

			var p = _splashes.Emit( at.WithZ( floor ), Random.Shared.NextSingle() );
			p.StartPosition = new Vector3( sprite, Random.Shared.Float( 0.4f, 0.55f ) * MathF.Min( 1f, cover * MathF.Min( 1f / share, 3f ) ), floor );
			p.StartAngles = new Angles( minWidth, 0f, 0f );
			p.TimeScale = 1f / life;
			p.Alpha = 0f;
			p.Size = Vector3.Zero;
			p.Velocity = Vector3.Zero;
			made++;
		}

		_splashTried += tries;
		_splashMade += made;
		if ( _splashTried >= 2000 )
		{
			_splashAccept = MathF.Max( MathX.Lerp( _splashAccept, (float)_splashMade / _splashTried, 0.5f ), 0.1f );
			_splashTried = _splashMade = 0;
		}
	}

	// ── Rings on the puddles ────────────────────────────────────────────────────

	/// <summary> The most rings started a second, and in a frame. </summary>
	private const float RippleBudget = 6000f;
	private const int RipplesPerFrame = 400;

	/// <summary> How fast a ring's leading crest spreads: about 0.2 m/s, as a drop's capillary waves do. </summary>
	private const float RippleSpeed = 8f;

	/// <summary> How far over the ground the rings are drawn, so the ground doesn't cut them. </summary>
	private const float RippleLift = 0.35f;

	private readonly List<float> _rippleRates = new();
	private readonly List<float> _rippleDistances = new();

	/// <summary>
	/// A ring for each drop over 0.5 mm that lands on a puddle's water in view: out to a distance every one, past it a
	/// share (reach / d)², so they come to the budget. Each starts in a random wet cell of the puddle's shape and fades
	/// out before its crest would reach the water's edge.
	/// </summary>
	private void UpdateRipples( CameraComponent camera, Vector3 eye, float rate, float opacity, float darkening, float flash )
	{
		if ( !_ripples.IsValid() || !_rippleController.IsValid() ) return;

		_rippleController.Opacity = opacity;
		_rippleController.Tint = Shade( Haze( darkening, flash ), RippleShade );

		var waters = _puddles.Waters;
		var flux = DropFlux( rate, 0.5f ) * opacity;
		if ( waters.Count == 0 || flux <= 0f ) return;

		var forward = camera.WorldRotation.Forward;
		var half = MathF.Acos( ViewCone( camera ) );
		_rippleRates.Clear();
		_rippleDistances.Clear();
		var all = 0f;
		foreach ( var water in waters )
		{
			var to = water.Centre - eye;
			var distance = MathF.Max( to.Length, 1f );
			// In view, give or take its own size.
			var off = MathF.Acos( Math.Clamp( Vector3.Dot( to, forward ) / distance, -1f, 1f ) );
			var inView = off <= half + MathF.Asin( MathF.Min( 0.75f * water.Diameter / distance, 1f ) );
			var perSecond = inView ? flux * water.Area * water.Alpha : 0f;
			_rippleRates.Add( perSecond );
			_rippleDistances.Add( distance );
			all += perSecond;
		}
		if ( all <= 0f ) return;

		var reach = float.PositiveInfinity;
		if ( all > RippleBudget )
		{
			var low = 0f;
			var high = 4000f;
			for ( var i = 0; i < 24; i++ )
			{
				var mid = 0.5f * (low + high);
				if ( ThinnedRate( mid ) > RippleBudget ) high = mid;
				else low = mid;
			}
			reach = low;
		}

		var total = 0f;
		for ( var i = 0; i < _rippleRates.Count; i++ )
		{
			_rippleRates[i] *= RippleShare( reach, _rippleDistances[i] );
			total += _rippleRates[i];
		}
		if ( total <= 0f ) return;

		_rippleCarry += total * Time.Delta;
		var count = (int)_rippleCarry;
		_rippleCarry -= count;
		count = Math.Min( count, RipplesPerFrame );

		var lambda = MarshallPalmerLambda( rate );
		for ( var n = 0; n < count && !_ripples.IsFull; n++ )
		{
			var pick = Random.Shared.NextSingle() * total;
			var i = 0;
			while ( i < _rippleRates.Count - 1 && pick >= _rippleRates[i] )
			{
				pick -= _rippleRates[i];
				i++;
			}
			var water = waters[i];
			if ( water.WetCells <= 0 ) continue;

			var cell = RainPuddles.WetOrder( water.Shape )[Random.Shared.Next( water.WetCells )];
			var u = (cell % PuddleShapes.Cells + Random.Shared.NextSingle()) / PuddleShapes.Cells;
			var v = (cell / PuddleShapes.Cells + Random.Shared.NextSingle()) / PuddleShapes.Cells;

			// How far the water reaches round the cell: the widest of its rings still all under water, less the most a
			// point in the cell can be off its middle.
			var tables = PuddleShapes.Tables( water.Shape );
			var k = 0;
			while ( k + 1 < PuddleShapes.RingReach
				&& tables[(k + 1) * PuddleShapes.Cells * PuddleShapes.Cells + cell] > water.Threshold )
				k++;
			var room = (k + 0.29f) * water.Diameter / PuddleShapes.Cells;

			var diameter = DiameterFrom( Random.Shared.NextSingle(), lambda, 0.5f );
			var speed = RippleSpeed * Random.Shared.Float( 0.85f, 1.15f );
			var life = MathF.Min( (0.25f + 0.06f * diameter) * Random.Shared.Float( 0.8f, 1.2f ), room / speed );
			if ( life < 0.06f ) continue;

			var share = RippleShare( reach, _rippleDistances[i] );
			var alpha = MathF.Min( Random.Shared.Float( 0.28f, 0.4f ) * MathF.Min( 1f / share, 2f ), 0.6f ) * water.Alpha;

			var p = _ripples.Emit( water.PointAt( u, v ) + Vector3.Up * RippleLift, Random.Shared.NextSingle() );
			p.StartPosition = new Vector3( speed * life, alpha, 0f );
			p.Angles = new Angles( 90f, Random.Shared.NextSingle() * 360f, 0f );
			p.TimeScale = 1f / life;
			p.Alpha = 0f;
			p.Size = Vector3.Zero;
			p.Velocity = Vector3.Zero;
		}
	}

	private static float RippleShare( float reach, float distance ) =>
		distance <= reach ? 1f : (reach / distance) * (reach / distance);

	private float ThinnedRate( float reach )
	{
		var sum = 0f;
		for ( var i = 0; i < _rippleRates.Count; i++ )
			sum += _rippleRates[i] * RippleShare( reach, _rippleDistances[i] );
		return sum;
	}

	// ── Sound ───────────────────────────────────────────────────────────────────

	/// <summary> The light and heavy loops' gains at a rate (mm/h), as <c>Tools/rain_sounds.py</c>'s mix_weights. </summary>
	public static (float Light, float Heavy) MixWeights( float rate )
	{
		var w = Math.Clamp( MathF.Log( MathF.Max( rate, 1e-3f ) / 2f ) / MathF.Log( 10f ), 0f, 1f );
		var light = MathF.Cos( w * MathF.PI / 2f ) * (rate < 2f ? RateGain( rate, 2f ) : 1f);
		var heavy = MathF.Sin( w * MathF.PI / 2f ) * (rate > 20f ? RateGain( rate, 20f ) : 1f);
		return (light, heavy);
	}

	/// <summary> 5 dB a decade of rate past the rate a loop was made at. </summary>
	private static float RateGain( float rate, float design ) => MathF.Pow( 10f, 5f * MathF.Log10( MathF.Max( rate, 0.01f ) / design ) / 20f );

	private void UpdateSound( Vector3 eye, float rate, float opacity )
	{
		var (outdoor, under) = _grid.Exposure( eye );
		var blend = 1f - MathF.Exp( -Time.Delta * 3f );
		_outdoorGain += (outdoor - _outdoorGain) * blend;
		_underGain += (under - _underGain) * blend;

		var (light, heavy) = MixWeights( rate );
		var roof = _underGain * RateGain( rate, 20f );
		var fade = opacity;

		Loop( ref _light, ref _lightBase, LightLoop, light * _outdoorGain * fade );
		Loop( ref _heavy, ref _heavyBase, HeavyLoop, heavy * _outdoorGain * fade );
		Loop( ref _roof, ref _roofBase, RoofLoop, roof * fade );
	}

	private static void Loop( ref SoundHandle handle, ref float baseVolume, string sound, float gain )
	{
		if ( gain <= 0.001f )
		{
			if ( handle.IsValid() ) handle.Volume = 0f;
			return;
		}
		if ( !handle.IsValid() || handle.Finished )
		{
			handle = Sound.Play( sound );
			if ( !handle.IsValid() ) return;
			baseVolume = handle.Volume;
		}
		handle.Volume = baseVolume * gain;
	}

	private void StopSounds( float fade )
	{
		if ( _light.IsValid() ) _light.Stop( fade );
		if ( _heavy.IsValid() ) _heavy.Stop( fade );
		if ( _roof.IsValid() ) _roof.Stop( fade );
		foreach ( var thunder in _thunder )
			if ( thunder.Handle.IsValid() ) thunder.Handle.Stop( fade * 4f );
		_thunder.Clear();
		_rumbles.Clear();
	}

	// ── Lightning ───────────────────────────────────────────────────────────────

	private const string ThunderNear = "sounds/weather/thunder_near.sound";
	private const string ThunderMid = "sounds/weather/thunder_mid.sound";
	private const string ThunderFar = "sounds/weather/thunder_far.sound";

	/// <summary> The speed of sound in cool, wet air (m/s). </summary>
	private const float SoundSpeed = 338f;

	/// <summary> A flash in the cloud is about this high (m), so its thunder comes from at least that far. </summary>
	private const float CloudFlashHeight = 6000f;

	/// <summary> Strikes dev_thunder asked for, started on the next frame. </summary>
	private static readonly List<Weather.Schedule.Strike> Requested = new();

	private readonly record struct Rumble( float At, Weather.Schedule.Strike Strike );
	private readonly record struct Thunder( SoundHandle Handle, Vector3 Direction, float Volume );

	private readonly List<Rumble> _rumbles = new();
	private readonly List<Thunder> _thunder = new();
	private readonly List<(float Start, Weather.Schedule.Strike Strike)> _flashes = new();
	private float _strikesTo = float.NaN;
	private WeatherKind _strikesKind;
	private int _strikesSeed;

	/// <summary> A strike <paramref name="distance"/> m off on a bearing (radians), seen and heard on this machine only (dev_thunder). </summary>
	public static void RequestStrike( float distance, float bearing, bool cloud )
	{
		lock ( Requested )
			Requested.Add( new Weather.Schedule.Strike( 0f, distance, bearing, cloud, Random.Shared.Next() ) );
	}

	/// <summary>
	/// Starts the flashes that have come since the last frame, and their thunder once its sound gets here, and returns
	/// how bright the flashes are now. A machine that joins mid-match starts from then, so it doesn't see the old ones.
	/// </summary>
	private float UpdateLightning( Vector3 eye )
	{
		var clock = (float)RealTime.Now;
		if ( Weather.IsValid() && Weather.IsRaining )
		{
			var now = (float)Weather.Elapsed;
			if ( float.IsNaN( _strikesTo ) || Weather.Kind != _strikesKind || Weather.Seed != _strikesSeed || now < _strikesTo )
			{
				_strikesTo = now;
				_strikesKind = Weather.Kind;
				_strikesSeed = Weather.Seed;
			}

			foreach ( var strike in Weather.Schedule.Strikes( Weather.Kind, Weather.Seed ) )
			{
				if ( strike.Time <= _strikesTo ) continue;
				if ( strike.Time > now ) break;
				Begin( strike, clock - (now - strike.Time) );
			}
			_strikesTo = now;
		}

		lock ( Requested )
		{
			foreach ( var strike in Requested ) Begin( strike, clock );
			Requested.Clear();
		}

		for ( var i = _rumbles.Count - 1; i >= 0; i-- )
		{
			if ( _rumbles[i].At > clock ) continue;
			PlayThunder( _rumbles[i].Strike, eye );
			_rumbles.RemoveAt( i );
		}

		for ( var i = _thunder.Count - 1; i >= 0; i-- )
		{
			var thunder = _thunder[i];
			if ( !thunder.Handle.IsValid() || thunder.Handle.Finished )
			{
				_thunder.RemoveAt( i );
				continue;
			}
			// It comes from that way wherever the camera goes, quieter indoors, where only its lows come through.
			thunder.Handle.Position = eye + thunder.Direction * 1500f;
			thunder.Handle.Volume = thunder.Volume * (0.4f + 0.6f * _outdoorGain);
		}

		var flash = 0f;
		for ( var i = _flashes.Count - 1; i >= 0; i-- )
		{
			var t = clock - _flashes[i].Start;
			if ( t > 1.2f )
			{
				_flashes.RemoveAt( i );
				continue;
			}
			flash += Weather.Schedule.FlashAt( _flashes[i].Strike, t );
		}
		return MathF.Min( flash, 2f );
	}

	private void Begin( Weather.Schedule.Strike strike, float start )
	{
		_flashes.Add( (start, strike) );
		var heard = HeardFrom( strike );
		if ( heard <= Weather.Schedule.AudibleRange )
			_rumbles.Add( new Rumble( start + heard / SoundSpeed, strike ) );
	}

	/// <summary> How far the nearest part of the channel is (m): a ground strike's foot, or the cloud over a flash in it. </summary>
	private static float HeardFrom( Weather.Schedule.Strike strike ) => strike.IsCloud
		? MathF.Sqrt( strike.Distance * strike.Distance + CloudFlashHeight * CloudFlashHeight )
		: strike.Distance;

	/// <summary>
	/// Each set was made for a distance (<c>Tools/thunder_sounds.py</c>): within 2 km the crack and the tearing of the
	/// near channel, 2-6 km a peal, past that a low rumble. Within its band the level goes by the distance, squeezed as
	/// the rest of the mix is.
	/// </summary>
	private void PlayThunder( Weather.Schedule.Strike strike, Vector3 eye )
	{
		var distance = HeardFrom( strike );
		var (path, reference) = distance < 2000f ? (ThunderNear, 1000f) : distance < 6000f ? (ThunderMid, 3500f) : (ThunderFar, 9000f);

		// A ground strike is heard most from its lower channel, low over the horizon; one in the cloud from up in it.
		var elevation = MathF.Atan2( strike.IsCloud ? CloudFlashHeight : 1200f, MathF.Max( strike.Distance, 300f ) );
		var direction = new Vector3( MathF.Cos( strike.Bearing ) * MathF.Cos( elevation ),
			MathF.Sin( strike.Bearing ) * MathF.Cos( elevation ), MathF.Sin( elevation ) );
		var handle = Sound.Play( path, eye + direction * 1500f );
		if ( !handle.IsValid() ) return;

		handle.DistanceAttenuation = false;
		handle.OcclusionEnabled = false;
		// A long channel, not a point: it has a direction, but not as sharp as a gunshot's.
		handle.SpacialBlend = 0.6f;
		var volume = handle.Volume * Math.Clamp( MathF.Pow( reference / distance, 0.43f ), 0.35f, 2f );
		handle.Volume = volume * (0.4f + 0.6f * _outdoorGain);
		_thunder.Add( new Thunder( handle, direction, volume ) );
	}

	// ── Effects and their sprites ───────────────────────────────────────────────

	private ParticleEffect CreateEffect<T>( string name, Sprite sprite, int max, float lifetime, bool faceVelocity,
		ParticleSpriteRenderer.BillboardAlignment alignment, Sandbox.Rendering.FilterMode filter )
		where T : ParticleController, new()
	{
		var go = new GameObject( GameObject, true, name );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.NetworkMode = NetworkMode.Never;
		go.Tags.Add( "particles" );

		var effect = go.AddComponent<ParticleEffect>();
		effect.MaxParticles = max;
		effect.Lifetime = lifetime;
		effect.LocalSpace = 0f;

		var renderer = go.AddComponent<ParticleSpriteRenderer>();
		renderer.Sprite = sprite;
		renderer.Additive = false;
		renderer.Lighting = false;
		renderer.Shadows = false;
		renderer.DepthFeather = 0f;
		renderer.FaceVelocity = faceVelocity;
		renderer.SortMode = ParticleSpriteRenderer.ParticleSortMode.Unsorted;
		renderer.Alignment = alignment;
		renderer.TextureFilter = filter;

		go.AddComponent<T>();
		return effect;
	}

	private static Sprite _dropSprite, _splashSprite, _rippleSprite;

	/// <summary>
	/// A drop's streak: the length is the sprite's height (a sprite facing its velocity turns its up along it), solid
	/// across its middle and fading at both ends. Small, since it's drawn a pixel or two wide.
	/// </summary>
	private static Sprite DropSprite => _dropSprite ??= Sprite.FromTexture( MakeTexture( 8, 32, ( u, v ) =>
		SmoothStep( 0f, 0.35f, u ) * SmoothStep( 1f, 0.65f, u ) * SmoothStep( 0f, 0.2f, v ) * SmoothStep( 1f, 0.8f, v ) ) );

	/// <summary>
	/// A splash's crown seen from the side: a thin rim, the sheet of water flaring up from it with brighter edges, a few
	/// droplets thrown off its top, and a faint ring on the ground. Its base is 0.8125 of the way down.
	/// </summary>
	private static Sprite SplashSprite => _splashSprite ??= Sprite.FromTexture( MakeTexture( 32, 32, SplashAlpha ) );

	private static float SplashAlpha( float u, float v )
	{
		// In the 64-pixel layout the crown was drawn in: the rim round (32, 38), the ground ring at (32, 52).
		var x = u * 64f;
		var y = v * 64f;
		var alpha = 0f;

		// The ground ring, where the drop struck.
		alpha = MathF.Max( alpha, 0.25f * Ellipse( x, y, 32f, 52f, 24f, 2.5f, 1.5f ) );

		// The crown's wall: from half-width 20 at its rim (y 38) down to 9 at its base (y 52).
		if ( y >= 38f && y <= 52f )
		{
			var t = (y - 38f) / 14f;
			var half = MathX.Lerp( 20f, 9f, t );
			var across = MathF.Abs( x - 32f ) / half;
			if ( across <= 1f )
			{
				var edge = SmoothStep( 0.75f, 1f, across ) * (1f - SmoothStep( 0.97f, 1.05f, across ));
				alpha = MathF.Max( alpha, (0.35f + 0.6f * edge) * (1f - 0.5f * t) );
			}
		}

		// The rim.
		alpha = MathF.Max( alpha, 0.9f * Ellipse( x, y, 32f, 38f, 20f, 4f, 1.5f ) );

		// Droplets thrown up off the rim.
		ReadOnlySpan<float> drops = stackalloc float[] { 14f, 30f, 22f, 25f, 32f, 22f, 42f, 26f, 50f, 31f, 18f, 21f, 46f, 19f };
		for ( var i = 0; i < drops.Length; i += 2 )
		{
			var d = MathF.Sqrt( (x - drops[i]) * (x - drops[i]) + (y - drops[i + 1]) * (y - drops[i + 1]) );
			alpha = MathF.Max( alpha, 0.85f * (1f - SmoothStep( 1.6f, 3.2f, d )) );
		}

		return Math.Clamp( alpha, 0f, 1f );
	}

	/// <summary>
	/// A drop's ring on water, seen from above: the leading crest 0.9 of the way out and the smaller ripples following it
	/// inside, each fainter. It lies flat, so it needs its mips, or far rings shimmer.
	/// </summary>
	private static Sprite RippleSprite => _rippleSprite ??= Sprite.FromTexture( MakeTexture( 64, 64, RippleAlpha ) );

	private static float RippleAlpha( float u, float v )
	{
		var dx = u - 0.5f;
		var dy = v - 0.5f;
		var r = 2f * MathF.Sqrt( dx * dx + dy * dy );
		var alpha = Crest( r, 0.9f, 0.035f ) + 0.5f * Crest( r, 0.72f, 0.03f ) + 0.25f * Crest( r, 0.55f, 0.03f );
		return Math.Clamp( alpha, 0f, 1f ) * (1f - SmoothStep( 0.96f, 1f, r ));
	}

	private static float Crest( float r, float at, float width ) => MathF.Exp( -((r - at) / width) * ((r - at) / width) );

	/// <summary> A ring along an ellipse's outline, <paramref name="thickness"/> pixels thick. </summary>
	private static float Ellipse( float x, float y, float cx, float cy, float rx, float ry, float thickness )
	{
		var dx = (x - cx) / rx;
		var dy = (y - cy) / ry;
		var r = MathF.Sqrt( dx * dx + dy * dy );
		// How far off the outline in pixels, roughly.
		var off = MathF.Abs( r - 1f ) * MathF.Min( rx, ry * 3f );
		return 1f - SmoothStep( thickness * 0.5f, thickness * 1.5f, off );
	}

	private static Texture MakeTexture( int width, int height, Func<float, float, float> alpha )
	{
		var data = new byte[width * height * 4];
		for ( var y = 0; y < height; y++ )
		{
			for ( var x = 0; x < width; x++ )
			{
				var a = alpha( (x + 0.5f) / width, (y + 0.5f) / height );
				var i = (y * width + x) * 4;
				data[i] = data[i + 1] = data[i + 2] = byte.MaxValue;
				data[i + 3] = (byte)(Math.Clamp( a, 0f, 1f ) * 255f + 0.5f);
			}
		}
		return Texture.Create( width, height ).WithStaticUsage().WithData( data ).WithMips().Finish();
	}

	/// <summary> Hermite smoothstep from <paramref name="edge0"/> to <paramref name="edge1"/>; the edges may be either way round. </summary>
	public static float SmoothStep( float edge0, float edge1, float x )
	{
		var t = Math.Clamp( (x - edge0) / (edge1 - edge0), 0f, 1f );
		return t * t * (3f - 2f * t);
	}

	// ── Shelter ─────────────────────────────────────────────────────────────────

	/// <summary>
	/// Where the sky is open round the camera, on a grid of 32-unit columns. Each column is probed once (and again when
	/// the camera has climbed or dropped a storey, or in turn every so often for doors and moving things): a trace down
	/// from above the camera finds the first thing rain would land on, and a trace up from there finds whether anything
	/// is over it. The drops read it from the particle threads, so it's plain arrays; the main thread writes it before
	/// they step.
	/// </summary>
	public sealed class ShelterGrid
	{
		public const int N = 64;
		public const float Cell = 32f;
		/// <summary> Columns probed out to this many cells from the camera's: past the furthest drops (900). </summary>
		private const int Reach = 29;
		private const int ProbesPerFrame = 48;
		private const int RefreshesPerFrame = 6;
		/// <summary> A column is probed again once the camera is this much higher or lower than when it was probed. </summary>
		private const float ReprobeHeight = 400f;

		public const byte Unknown = 0, Open = 1, Covered = 2;

		internal static readonly string[] Ignore =
			{ "player", "movement", "ragdoll", "trigger", "playerclip", "enemy", "particles", "viewer", "corpse", "water" };

		private readonly int[] _keyX = new int[N * N];
		private readonly int[] _keyY = new int[N * N];
		private readonly float[] _floor = new float[N * N];
		private readonly float[] _probeZ = new float[N * N];
		private readonly byte[] _state = new byte[N * N];

		private static readonly (int X, int Y)[] Spiral = BuildSpiral();
		private int _refresh;
		private float _mapTop = float.MaxValue;
		private RealTimeSince _sinceMapTop = 999f;

		public ShelterGrid()
		{
			Array.Fill( _keyX, int.MinValue );
			Array.Fill( _keyY, int.MinValue );
		}

		private static (int X, int Y)[] BuildSpiral()
		{
			var cells = new List<(int X, int Y)>();
			for ( var y = -Reach; y <= Reach; y++ )
				for ( var x = -Reach; x <= Reach; x++ )
					cells.Add( (x, y) );
			return cells.OrderBy( c => c.X * c.X + c.Y * c.Y ).ToArray();
		}

		private static int Index( int cx, int cy ) => ((cx % N + N) % N) * N + ((cy % N + N) % N);

		/// <summary> What's known of the column over (x, y), and where rain lands in it. </summary>
		public byte Lookup( float x, float y, out float floor )
		{
			var cx = (int)MathF.Floor( x / Cell );
			var cy = (int)MathF.Floor( y / Cell );
			var i = Index( cx, cy );
			floor = _floor[i];
			if ( _keyX[i] != cx || _keyY[i] != cy ) return Unknown;
			return _state[i];
		}

		/// <summary> Open to the sky, with level ground under it and its four neighbours (no splashes on an edge). </summary>
		public bool IsFlatOpenGround( float x, float y, out float floor )
		{
			if ( Lookup( x, y, out floor ) != Open ) return false;
			for ( var i = 0; i < 4; i++ )
			{
				var nx = x + (i == 0 ? Cell : i == 1 ? -Cell : 0f);
				var ny = y + (i == 2 ? Cell : i == 3 ? -Cell : 0f);
				if ( Lookup( nx, ny, out var other ) != Open || MathF.Abs( other - floor ) > 4f ) return false;
			}
			return true;
		}

		public void Update( Scene scene, Vector3 eye )
		{
			if ( _sinceMapTop > 5f )
			{
				_sinceMapTop = 0f;
				var maps = scene.GetAllComponents<MapInstance>().Where( m => m.IsValid() && m.IsLoaded ).ToList();
				_mapTop = maps.Count > 0 ? maps.Max( m => m.Bounds.Maxs.z ) : float.MaxValue;
			}

			var ox = (int)MathF.Floor( eye.x / Cell );
			var oy = (int)MathF.Floor( eye.y / Cell );

			var probes = 0;
			foreach ( var (sx, sy) in Spiral )
			{
				var cx = ox + sx;
				var cy = oy + sy;
				var i = Index( cx, cy );
				var stale = _keyX[i] != cx || _keyY[i] != cy || MathF.Abs( eye.z - _probeZ[i] ) > ReprobeHeight;
				if ( !stale ) continue;
				Probe( scene, cx, cy, eye.z );
				if ( ++probes >= ProbesPerFrame ) break;
			}

			for ( var r = 0; r < RefreshesPerFrame; r++ )
			{
				_refresh = (_refresh + 1) % Spiral.Length;
				var (sx, sy) = Spiral[_refresh];
				Probe( scene, ox + sx, oy + sy, eye.z );
			}
		}

		private void Probe( Scene scene, int cx, int cy, float eyeZ )
		{
			var x = (cx + 0.5f) * Cell;
			var y = (cy + 0.5f) * Cell;
			var top = eyeZ + 900f;
			var bottom = top - 4000f;

			byte state;
			float floor;
			var down = scene.Trace.Ray( new Vector3( x, y, top ), new Vector3( x, y, bottom ) ).WithoutTags( Ignore ).Run();
			if ( down.StartedSolid )
			{
				state = Covered;
				floor = top;
			}
			else if ( !down.Hit )
			{
				state = Open;
				floor = bottom;
			}
			else
			{
				floor = down.HitPosition.z;
				var up = scene.Trace.Ray( new Vector3( x, y, top ), new Vector3( x, y, top + 32000f ) ).WithoutTags( Ignore ).Run();
				state = up.StartedSolid || (up.Hit && !IsSkyCeiling( up, eyeZ )) ? Covered : Open;
			}

			var i = Index( cx, cy );
			_floor[i] = floor;
			_probeZ[i] = eyeZ;
			_state[i] = state;
			_keyX[i] = cx;
			_keyY[i] = cy;
		}

		/// <summary> The map's sky brush or its lid, not a roof: rain comes from up there. </summary>
		internal bool IsSkyCeiling( SceneTraceResult up, float eyeZ )
		{
			var surface = up.Surface?.ResourceName ?? "";
			if ( surface.Contains( "sky", StringComparison.OrdinalIgnoreCase ) ) return true;
			if ( up.HitPosition.z >= _mapTop - 256f && up.Normal.z < -0.9f ) return true;
			return up.HitPosition.z > eyeZ + 3000f;
		}

		/// <summary>
		/// How much of the rain's sound reaches the camera: the open sky round it (near columns counting most), less under
		/// a roof; and how loud the rain on a roof over it is.
		/// </summary>
		public (float Outdoor, float Under) Exposure( Vector3 eye )
		{
			const int radius = 12;
			var ox = (int)MathF.Floor( eye.x / Cell );
			var oy = (int)MathF.Floor( eye.y / Cell );
			float open = 0f, known = 0f;
			for ( var dy = -radius; dy <= radius; dy++ )
			{
				for ( var dx = -radius; dx <= radius; dx++ )
				{
					var cx = ox + dx;
					var cy = oy + dy;
					var i = Index( cx, cy );
					if ( _keyX[i] != cx || _keyY[i] != cy || _state[i] == Unknown ) continue;
					var distance = MathF.Sqrt( dx * dx + dy * dy ) * Cell;
					var weight = 1f / (1f + distance / 100f);
					known += weight;
					if ( _state[i] == Open && _floor[i] <= eye.z + 100f ) open += weight;
				}
			}

			var share = known > 0f ? open / known : 1f;
			var here = Lookup( eye.x, eye.y, out var floor );
			var roofed = here == Covered || (here == Open && floor > eye.z + 8f);
			var outdoor = (0.18f + 0.82f * MathF.Pow( share, 0.7f )) * (roofed ? 0.4f : 1f);

			var under = here == Open && floor > eye.z + 8f
				? Math.Clamp( 1f - (floor - eye.z) / 700f, 0.15f, 1f )
				: here == Covered ? 0.25f : 0f;
			return (outdoor, under);
		}
	}

	// ── The overcast look ───────────────────────────────────────────────────────

	/// <summary>
	/// The sky clouds over, the sun goes weak and grey, the fog closes in to rain's visibility and reflections lose the
	/// blue sky. Every value it changes is kept and put back exactly when the rain has gone, the view goes, or the
	/// scene unloads. Cloud maps' baked light isn't changed.
	/// </summary>
	private sealed class RainLook
	{
		private readonly record struct SkyState( Color Tint, Material Material );
		private readonly record struct SunState( Color Light, Color Sky );
		private readonly record struct FogState( Color Color, float Height, float Start, float End, float Falloff );

		private readonly Dictionary<SkyBox2D, SkyState> _skies = new();
		private readonly Dictionary<DirectionalLight, SunState> _suns = new();
		private readonly Dictionary<GradientFog, FogState> _fogs = new();
		private readonly Dictionary<EnvmapProbe, Color> _probes = new();
		private SceneWorld _world;
		private Sandbox.Rendering.GradientFogSetup? _worldFog;
		private RealTimeSince _sinceScan = 999f;
		private static Material _overcast;

		/// <summary> The overcast sky (<c>Tools/rain_sky.py</c>). </summary>
		private static Material Overcast => _overcast ??= Material.Load( "materials/weather/overcast_sky.vmat" );

		/// <summary>
		/// <paramref name="flash"/> is the lightning's light now (<see cref="Weather.Schedule.FlashAt"/>): it lights the
		/// cloud, the sky's light and the rain's haze a bluish white, and the scene a little from the sun's side.
		/// </summary>
		public void Apply( Scene scene, float k, float rate, float flash )
		{
			if ( _sinceScan > 1f )
			{
				_sinceScan = 0f;
				Scan( scene );
			}

			var dark = MathX.Lerp( 1f, 0.62f, SmoothStep( 1f, 30f, rate ) );

			foreach ( var (sky, was) in _skies )
			{
				if ( !sky.IsValid() ) continue;
				var material = k > 0.5f && Overcast is not null ? Overcast : was.Material;
				if ( sky.SkyMaterial != material ) sky.SkyMaterial = material;
				sky.Tint = Lit( Lerp( was.Tint, new Color( dark, dark, dark, was.Tint.a ), k ), flash * 3f );
			}

			// Under a deck of cloud the sun is a pale disc at a seventh to a third of its light, and the sky's light grey.
			var sunShare = MathX.Lerp( 0.35f, 0.15f, SmoothStep( 0.5f, 20f, rate ) );
			foreach ( var (sun, was) in _suns )
			{
				if ( !sun.IsValid() ) continue;
				var lum = Luminance( was.Light ) * sunShare;
				sun.LightColor = Lit( Lerp( was.Light, new Color( 0.93f * lum, 0.96f * lum, lum, was.Light.a ), k ), flash * 0.8f );
				var sky = Luminance( was.Sky ) * dark;
				sun.SkyColor = Lit( Lerp( was.Sky, new Color( sky, sky, sky, was.Sky.a ), k ), flash * 4f );
			}

			// Rain's visibility (km): 1/V = 0.125 + 0.25 R^0.63 / 3.912, the haze's 8 km dry.
			var visibility = 1f / (0.125f + 0.25f * MathF.Pow( MathF.Max( rate, 0f ), 0.63f ) / 3.912f);
			var end = 0.75f * visibility * 39370f;
			var haze = Haze( dark, flash );
			var grey = new Color( haze.r, haze.g, haze.b, 0.98f );
			foreach ( var (fog, was) in _fogs )
			{
				if ( !fog.IsValid() ) continue;
				fog.Color = Lerp( was.Color, grey, k );
				fog.StartDistance = MathX.Lerp( was.Start, 0f, k );
				fog.EndDistance = MathX.Lerp( was.End, end, k );
				fog.FalloffExponent = MathX.Lerp( was.Falloff, 0.5f, k );
				fog.Height = MathX.Lerp( was.Height, MathF.Max( was.Height, 40000f ), k );
			}

			// With no fog component, the world's own fog.
			if ( _fogs.Count == 0 && scene.SceneWorld is { } world )
			{
				if ( _world != world )
				{
					_world = world;
					_worldFog = world.GradientFog;
				}

				var was = _worldFog ?? default;
				var f = was;
				var from = was.Enabled ? was.MaximumOpacity : 0f;
				f.Enabled = true;
				f.Color = Lerp( was.Enabled ? was.Color : grey, grey, k );
				f.MaximumOpacity = MathX.Lerp( from, 0.98f, k );
				f.StartDistance = MathX.Lerp( was.Enabled ? was.StartDistance : 0f, 0f, k );
				f.EndDistance = MathX.Lerp( was.Enabled ? was.EndDistance : end, end, k );
				f.DistanceFalloffExponent = MathX.Lerp( was.Enabled ? was.DistanceFalloffExponent : 0.5f, 0.5f, k );
				if ( !was.Enabled )
				{
					f.StartHeight = -20000f;
					f.EndHeight = 60000f;
					f.VerticalFalloffExponent = 1f;
				}
				world.GradientFog = f;
			}

			// The probes' reflections hold the clear sky's blue: grey it, and darken it.
			var tint = new Color( 0.72f, 0.68f, 0.62f );
			foreach ( var (probe, was) in _probes )
			{
				if ( !probe.IsValid() ) continue;
				probe.TintColor = Lerp( was, new Color( was.r * tint.r, was.g * tint.g, was.b * tint.b, was.a ), k );
			}
		}

		private void Scan( Scene scene )
		{
			foreach ( var sky in scene.GetAllComponents<SkyBox2D>() )
				if ( !_skies.ContainsKey( sky ) ) _skies[sky] = new SkyState( sky.Tint, sky.SkyMaterial );
			foreach ( var sun in scene.GetAllComponents<DirectionalLight>() )
				if ( !_suns.ContainsKey( sun ) ) _suns[sun] = new SunState( sun.LightColor, sun.SkyColor );
			foreach ( var fog in scene.GetAllComponents<GradientFog>() )
				if ( !_fogs.ContainsKey( fog ) )
					_fogs[fog] = new FogState( fog.Color, fog.Height, fog.StartDistance, fog.EndDistance, fog.FalloffExponent );
			foreach ( var probe in scene.GetAllComponents<EnvmapProbe>() )
				if ( !_probes.ContainsKey( probe ) ) _probes[probe] = probe.TintColor;

			// A fog component that's appeared after the world's own was taken over: give the world's back first.
			if ( _fogs.Count > 0 && _world is not null )
			{
				if ( _world.IsValid() && _worldFog is { } fog ) _world.GradientFog = fog;
				_world = null;
				_worldFog = null;
			}
		}

		public void Restore()
		{
			foreach ( var (sky, was) in _skies )
			{
				if ( !sky.IsValid() ) continue;
				if ( sky.SkyMaterial != was.Material ) sky.SkyMaterial = was.Material;
				sky.Tint = was.Tint;
			}
			foreach ( var (sun, was) in _suns )
			{
				if ( !sun.IsValid() ) continue;
				sun.LightColor = was.Light;
				sun.SkyColor = was.Sky;
			}
			foreach ( var (fog, was) in _fogs )
			{
				if ( !fog.IsValid() ) continue;
				fog.Color = was.Color;
				fog.Height = was.Height;
				fog.StartDistance = was.Start;
				fog.EndDistance = was.End;
				fog.FalloffExponent = was.Falloff;
			}
			foreach ( var (probe, was) in _probes )
				if ( probe.IsValid() ) probe.TintColor = was;
			if ( _world is not null && _world.IsValid() && _worldFog is { } worldFog )
				_world.GradientFog = worldFog;

			_skies.Clear();
			_suns.Clear();
			_fogs.Clear();
			_probes.Clear();
			_world = null;
			_worldFog = null;
			_sinceScan = 999f;
		}

		private static float Luminance( Color c ) => 0.2126f * c.r + 0.7152f * c.g + 0.0722f * c.b;

		/// <summary> A colour brightened by <paramref name="amount"/> times its own light, in lightning's bluish white. </summary>
		public static Color Lit( Color c, float amount )
		{
			if ( amount <= 0f ) return c;
			var l = Luminance( c ) * amount;
			return new Color( c.r + 0.85f * l, c.g + 0.9f * l, c.b + l, c.a );
		}

		private static Color Lerp( Color a, Color b, float t ) => new(
			a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t, a.a + (b.a - a.a) * t );
	}
}

/// <summary>
/// The rain's drops, each falling at its size's terminal speed and drifting with the wind, wrapping round the camera
/// so they never run out. Sizes follow Marshall and Palmer's spread for the rate. A drop shows only over open sky and
/// above where it would land (<see cref="RainView.ShelterGrid"/>), as a streak as long as it falls in a sixtieth of a
/// second (a frame at 60 fps), blurred by an eye's depth of field, and never thinner than a pixel and a half: widened,
/// it's fainter by as much, so a far drop is a faint thread and a near one a clear streak. Its colour is a share of the
/// haze's (<c>RainView.DropShade</c>), so it's a little darker than the sky and a little brighter than a dark wall.
/// </summary>
[Hide]
public sealed class RainDropParticles : ParticleController
{
	public const float MinDiameter = 0.3f;
	public const float MaxDiameter = 5f;

	/// <summary> What the drops need this frame, from the main thread: the particle threads read nothing else. </summary>
	public sealed record DropFrame( Vector3 Camera, Vector3 Wind, float Gust, float WindTime, float Lambda, float LambdaC,
		float Active, float PixelAngle, Color Tint, float Opacity, RainView.ShelterGrid Grid );

	/// <summary>
	/// How far a drop's streak runs (seconds of its fall): one frame at 60 fps, so at that rate each frame's streak meets
	/// the last one's end with no gap and no overlap. A 30 fps camera's shutter (0.033 s) drew streaks twice as long,
	/// which read as lines.
	/// </summary>
	private const float Exposure = 1f / 60f;

	/// <summary> The most a drop's streak covers what's behind it. </summary>
	private const float MaxAlpha = 0.35f;

	/// <summary>
	/// The eye's depth of field: focused at 15 m with a 4 mm pupil, a drop at distance d is blurred over
	/// <see cref="Aperture"/> |1 - d / <see cref="FocusDistance"/>| units, so near drops are soft and wide.
	/// </summary>
	private const float FocusDistance = 590f;
	private const float Aperture = 0.157f;

	public DropFrame Frame { get; set; }

	private DropFrame _frame;

	/// <summary> A drop's diameter (mm) from a uniform number, drawn from the exponential spread between 0.3 and 5 mm. </summary>
	public static float DiameterOf( float u, float lambda, float lambdaC ) =>
		Math.Clamp( MinDiameter - MathF.Log( 1f - u * lambdaC ) / lambda, MinDiameter, MaxDiameter );

	/// <summary> A drop's terminal speed (units/s) at its diameter (mm): Atlas, Srivastava and Sekhon's fit. </summary>
	public static float FallSpeed( float diameter ) =>
		MathF.Max( 9.65f - 10.3f * MathF.Exp( -0.6f * diameter ), 0.5f ) * WorldWind.UnitsPerMetre;

	protected override void OnBeforeStep( float delta ) => _frame = Frame;

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var f = _frame;
		if ( f is null || f.Grid is null )
		{
			p.Alpha = 0f;
			return;
		}

		var u = p.StartPosition.x;
		var radius = p.StartPosition.z;
		var diameter = DiameterOf( p.StartPosition.y, f.Lambda, f.LambdaC );
		var cam = f.Camera;
		var pos = p.Position;

		// Round the camera in plan: a drop that falls behind comes back in on the far side.
		var span = radius * 2f;
		var dx = pos.x - cam.x;
		var dy = pos.y - cam.y;
		dx -= span * MathF.Floor( (dx + radius) / span );
		dy -= span * MathF.Floor( (dy + radius) / span );
		pos.x = cam.x + dx;
		pos.y = cam.y + dy;

		var bottom = cam.z - 250f;
		var top = cam.z + 150f + 0.6f * radius;
		var state = f.Grid.Lookup( pos.x, pos.y, out var floor );
		var low = state == RainView.ShelterGrid.Open ? MathF.Max( bottom, floor ) : bottom;

		if ( pos.z < low || pos.z > top + 200f )
		{
			// Back to the top, somewhere new, keeping its phase so the drops don't fall in step.
			var height = MathF.Max( top - bottom, 1f );
			var phase = pos.z < low ? (low - pos.z) % height : (pos.z - top) % height;
			pos.z = top - phase;
			var seed = (uint)(u * 16777216f) ^ (uint)(p.StartPosition.y * 8388608f) * 31u ^ (uint)(p.Age * 977f);
			pos.x = cam.x + (Hash( seed ) * 2f - 1f) * radius;
			pos.y = cam.y + (Hash( seed ^ 0x9E3779B9u ) * 2f - 1f) * radius;
			state = f.Grid.Lookup( pos.x, pos.y, out floor );
		}
		p.Position = pos;

		var visible = state == RainView.ShelterGrid.Open && pos.z >= floor;
		var active = Math.Clamp( (f.Active - u) / 0.02f, 0f, 1f );
		if ( !visible || active <= 0f || f.Opacity <= 0f )
		{
			// Unseen, it only needs to keep falling: the gusts aren't worth working out.
			p.Velocity = f.Wind + Vector3.Down * FallSpeed( diameter );
			p.Alpha = 0f;
			return;
		}

		var velocity = WorldWind.Sample( pos, f.WindTime, f.Wind, f.Gust ) + Vector3.Down * FallSpeed( diameter );
		p.Velocity = velocity;

		var toDrop = pos - cam;
		var distance = toDrop.Length;
		var speed = velocity.Length;
		var along = distance > 0.01f && speed > 0.01f ? Vector3.Dot( velocity / speed, toDrop / distance ) : 0f;
		var across = MathF.Sqrt( MathF.Max( 0f, 1f - along * along ) );

		var trueWidth = diameter * 0.03937f;
		var blur = Aperture * MathF.Abs( 1f - distance / FocusDistance );
		var drawnWidth = MathF.Max( distance * f.PixelAngle * 1.5f, trueWidth + blur );
		var length = MathF.Max( speed * Exposure * across + blur, drawnWidth );
		p.Size = new Vector3( drawnWidth, length, 1f );

		// How many drops this one stands for (its layer's weight; 1 for a drop from before the weights).
		var weight = p.StartAngles.yaw > 0f ? p.StartAngles.yaw : 1f;
		// Drops differ: how they catch the light, how they tumble.
		var variance = 0.55f + 0.9f * Hash( (uint)(u * 16777216f) ^ 0xA511E9B3u );
		var edge = Math.Clamp( (radius - MathF.Max( MathF.Abs( dx ), MathF.Abs( dy ) )) / (0.3f * radius), 0f, 1f );
		var fadeTop = Math.Clamp( (top - pos.z) / 100f, 0f, 1f );
		// Right in front of the eye a drop is a blur gone in a frame.
		var near = RainView.SmoothStep( 12f, 60f, distance );
		var strength = 0.45f * MathF.Sqrt( diameter / 2f ) * (trueWidth / drawnWidth) * weight * variance;

		p.Color = f.Tint;
		p.Alpha = MathF.Min( strength, MaxAlpha ) * edge * fadeTop * near * active * f.Opacity;
	}

	private static float Hash( uint x )
	{
		x ^= x >> 16;
		x *= 0x7FEB352Du;
		x ^= x >> 15;
		x *= 0x846CA68Bu;
		x ^= x >> 16;
		return (x & 0xFFFFFF) / 16777216f;
	}
}

/// <summary>
/// Splashes on open, level ground in view: a crown that spreads and fades in 25-110 ms, bigger and longer for bigger
/// drops. The view emits them, each with its TimeScale set so its age runs 0-1 over its life; this plays each out.
/// </summary>
[Hide]
public sealed class RainSplashParticles : ParticleController
{
	public float Opacity { get; set; }
	public Color Tint { get; set; } = Color.White;

	private float _opacity;
	private Color _tint;

	protected override void OnBeforeStep( float delta )
	{
		_opacity = Opacity;
		_tint = Tint;
	}

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var t = Math.Clamp( p.Age, 0f, 1f );
		// Never under a pixel and a half across (the view made it fainter for that).
		var width = MathF.Max( p.StartPosition.x * (0.5f + 0.5f * t), p.StartAngles.pitch );
		p.Size = new Vector3( width, width, 1f );
		// The crown's base is 0.3125 of the sprite's height under its middle.
		p.Position = p.Position.WithZ( p.StartPosition.z + 0.3125f * width );
		p.Velocity = Vector3.Zero;
		p.Color = _tint;
		p.Alpha = p.StartPosition.y * MathF.Pow( 1f - t, 1.5f ) * _opacity;
	}
}

/// <summary>
/// The rings drops make on the puddles, lying flat on the water: each spreads at a capillary wave's 0.2 m/s from where
/// its drop struck and fades over a quarter to half a second, sooner where the water's edge is near. The view emits
/// them, each with its TimeScale set so its age runs 0-1 over its life; this plays each out.
/// </summary>
[Hide]
public sealed class RainRippleParticles : ParticleController
{
	public float Opacity { get; set; }
	public Color Tint { get; set; } = Color.White;

	private float _opacity;
	private Color _tint;

	protected override void OnBeforeStep( float delta )
	{
		_opacity = Opacity;
		_tint = Tint;
	}

	protected override void OnParticleStep( Particle p, float lifeDelta )
	{
		var t = Math.Clamp( p.Age, 0f, 1f );
		// The leading crest is 0.45 of the sprite's width out from its middle.
		var radius = 0.15f + p.StartPosition.x * t;
		var width = radius / 0.45f;
		p.Size = new Vector3( width, width, 1f );
		p.Velocity = Vector3.Zero;
		p.Color = _tint;
		p.Alpha = p.StartPosition.y * RainView.SmoothStep( 0f, 0.08f, t ) * MathF.Pow( 1f - t, 1.5f ) * _opacity;
	}
}
