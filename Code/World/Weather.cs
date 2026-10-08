namespace Facepunch;

public enum WeatherKind
{
	Clear,
	/// <summary> Drizzle: fine drops under 0.5 mm, 0.2-0.8 mm/h. </summary>
	Drizzle,
	/// <summary> Steady rain from a stratiform deck: 2-6 mm/h for the whole match. </summary>
	Steady,
	/// <summary> Showers from convective cells: dry gaps, then a few minutes of up to 40 mm/h. </summary>
	Showers,
}

/// <summary>
/// The match's weather. The host rolls it once the map has loaded (<see cref="RainChance"/>), and every machine works out
/// the rain rate from the kind, the seed and the time (<see cref="RainRate"/>), so only those are synced. Each machine
/// that draws shows it through its own <see cref="RainView"/>. Made on the host by <see cref="Ensure"/> and networked,
/// like <see cref="WorldWind"/>.
/// </summary>
[Title( "Weather" ), Category( "Environment" )]
public sealed class Weather : Component
{
	[Property, Sync( SyncFlags.FromHost )] public WeatherKind Kind { get; set; }
	[Sync( SyncFlags.FromHost )] public int Seed { get; set; }
	[Sync( SyncFlags.FromHost )] public TimeSince Elapsed { get; private set; }

	/// <summary> A rain rate (mm/h) that dev_weather set in place of the schedule, or below 0 for none. </summary>
	[Sync( SyncFlags.FromHost )] public float ForcedRate { get; set; } = -1f;

	/// <summary> The share of matches that have rain. </summary>
	public const float RainChance = 0.25f;

	/// <summary> If the map hasn't loaded by then, the weather is rolled anyway. </summary>
	private const float MapLoadTimeout = 60f;

	/// <summary>
	/// How much wetter than dry the dead grass is (percentage points of moisture), on the host. Fire spread reads it
	/// (<see cref="FireFuels.HeadRate"/>): CSIRO's grass model stops a fire spreading at about 20% moisture.
	/// </summary>
	public static float FuelWetting { get; private set; }

	/// <summary> The rain rate now (mm/h). </summary>
	public float RainRate => Kind == WeatherKind.Clear ? 0f : ForcedRate >= 0f ? ForcedRate : Schedule.RateAt( Kind, Seed, Elapsed );

	public bool IsRaining => Kind != WeatherKind.Clear;

	private bool _rolled;
	private TimeSince _sinceStart;
	private RainView _view;

	/// <summary> The rain on the grass (mm), drying with fine grass's one-hour timelag. </summary>
	private float _wetMm;

	private Vector3? _calmWind;
	private float _calmGust;

	protected override void OnStart()
	{
		_sinceStart = 0;
		if ( !IsProxy ) Elapsed = 0;
	}

	protected override void OnDestroy()
	{
		if ( _view.IsValid() ) _view.GameObject.Destroy();
		if ( !IsProxy ) FuelWetting = 0f;
	}

	protected override void OnUpdate()
	{
		if ( !IsProxy && !_rolled && (MapsLoaded() || _sinceStart > MapLoadTimeout) )
			Roll();

		if ( !Application.IsDedicatedServer && !_view.IsValid() && IsRaining )
		{
			var go = new GameObject( Scene, true, "Rain" );
			go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			go.NetworkMode = NetworkMode.Never;
			_view = go.AddComponent<RainView>();
			_view.Weather = this;
		}
	}

	protected override void OnFixedUpdate()
	{
		if ( IsProxy ) return;
		var dt = Time.Delta;
		_wetMm = (_wetMm + RainRate / 3600f * dt) * MathF.Exp( -dt / 3600f );
		// A tenth of a millimetre wets fine grass through; half a millimetre soaks it past where any fire runs.
		FuelWetting = 35f * (1f - MathF.Exp( -_wetMm / 0.3f ));
	}

	private bool MapsLoaded() => Scene.GetAllComponents<MapInstance>().All( m => !m.Active || m.IsLoaded );

	/// <summary> Somewhere with no sky (Reef Hall) never rains. </summary>
	private bool HasSky() => Scene.GetAllComponents<SkyBox2D>().Any()
		|| Scene.SceneWorld.SceneObjects.OfType<SceneSkyBox>().Any();

	private void Roll()
	{
		_rolled = true;
		Seed = Random.Shared.Next();
		Elapsed = 0;
		if ( !HasSky() || Random.Shared.NextSingle() >= RainChance )
		{
			Kind = WeatherKind.Clear;
			return;
		}

		// Of the rainy matches: a quarter drizzle, two fifths steady rain, the rest showers.
		var pick = Random.Shared.NextSingle();
		Set( pick < 0.25f ? WeatherKind.Drizzle : pick < 0.65f ? WeatherKind.Steady : WeatherKind.Showers, -1f );
		Log.Info( $"Weather: {Kind}" );
	}

	/// <summary> Sets the weather (host). A <paramref name="rate"/> of 0 or more holds the rain at that rate. </summary>
	public void Set( WeatherKind kind, float rate )
	{
		if ( IsProxy ) return;
		_rolled = true;
		Kind = kind;
		ForcedRate = kind == WeatherKind.Clear ? -1f : rate;
		if ( kind != WeatherKind.Clear && !HasSky() )
			Log.Warning( "Weather: this map has no sky, so the rain won't show." );
		SetWind( kind );
	}

	/// <summary>
	/// Rain comes with a front's wind: 2-4 m/s in drizzle, 3-6 m/s in rain, gusting harder in showers. The wind keeps
	/// its heading, and goes back to the calm when the weather clears.
	/// </summary>
	private void SetWind( WeatherKind kind )
	{
		var wind = WorldWind.Ensure( Scene );
		if ( !wind.IsValid() ) return;

		if ( kind == WeatherKind.Clear )
		{
			if ( _calmWind is { } calm )
			{
				wind.Velocity = calm;
				wind.GustStrength = _calmGust;
				_calmWind = null;
			}
			return;
		}

		_calmWind ??= wind.Velocity;
		if ( _calmWind == wind.Velocity ) _calmGust = wind.GustStrength;
		var heading = _calmWind.Value.WithZ( 0 );
		heading = heading.IsNearZeroLength ? new Vector3( 0.6f, -0.8f, 0f ) : heading.Normal;
		var random = new System.Random( Seed );
		var speed = kind == WeatherKind.Drizzle ? 2f + 2f * random.NextSingle() : 3f + 3f * random.NextSingle();
		wind.Velocity = heading * speed;
		wind.GustStrength = MathF.Max( _calmGust, kind == WeatherKind.Showers ? 0.55f : 0.4f );
	}

	/// <summary> The scene's weather, made on the host if there's none. </summary>
	public static Weather Ensure( Scene scene )
	{
		var existing = scene.GetAllComponents<Weather>().FirstOrDefault();
		if ( existing.IsValid() || !Networking.IsHost ) return existing;
		var go = new GameObject( scene, true, "Weather" );
		go.Flags |= GameObjectFlags.NotSaved;
		var weather = go.AddComponent<Weather>();
		go.NetworkSpawn();
		return weather;
	}

	/// <summary>
	/// The rain rate (mm/h) for a weather and seed at a time, the same on every machine.
	/// </summary>
	public static class Schedule
	{
		private readonly record struct Shower( float Start, float Duration, float Peak );

		private static readonly Dictionary<int, Shower[]> Showers = new();

		public static float RateAt( WeatherKind kind, int seed, float time ) => kind switch
		{
			// Drizzle and stratiform rain come and go slowly, with the deck's own lumps.
			WeatherKind.Drizzle => MathX.Lerp( 0.2f, 0.8f, Hash01( seed, 1 ) ) * Wander( seed, time, 0.3f ),
			WeatherKind.Steady => MathX.Lerp( 2f, 6f, Hash01( seed, 2 ) ) * Wander( seed, time, 0.35f ),
			WeatherKind.Showers => ShowerRate( seed, time ),
			_ => 0f,
		};

		/// <summary> 1 give or take <paramref name="amount"/>, wandering over ten minutes, three and under one. </summary>
		private static float Wander( int seed, float time, float amount )
		{
			var a = Hash01( seed, 3 ) * MathF.Tau;
			var b = Hash01( seed, 4 ) * MathF.Tau;
			var c = Hash01( seed, 5 ) * MathF.Tau;
			var wave = 0.57f * MathF.Sin( time * MathF.Tau / 600f + a )
				+ 0.29f * MathF.Sin( time * MathF.Tau / 170f + b )
				+ 0.14f * MathF.Sin( time * MathF.Tau / 45f + c );
			return MathF.Max( 0.25f, 1f + amount * wave );
		}

		/// <summary>
		/// A shower comes in hard (full within half a minute of its first drops), holds, then tails off over the last third.
		/// Most are moderate; a few are downpours.
		/// </summary>
		private static float ShowerRate( int seed, float time )
		{
			foreach ( var shower in ShowersOf( seed ) )
			{
				if ( time < shower.Start ) return 0f;
				var t = time - shower.Start;
				if ( t > shower.Duration ) continue;
				var rise = Math.Clamp( t / 30f, 0f, 1f );
				var tail = Math.Clamp( (shower.Duration - t) / (shower.Duration * 0.35f), 0f, 1f );
				var envelope = MathF.Sqrt( rise ) * tail * tail;
				return shower.Peak * envelope * Wander( seed + (int)shower.Start, time * 3f, 0.2f );
			}
			return 0f;
		}

		private static Shower[] ShowersOf( int seed )
		{
			lock ( Showers )
			{
				if ( Showers.TryGetValue( seed, out var list ) ) return list;
				var random = new System.Random( seed );
				var showers = new List<Shower>();
				// The first comes soon after the start, then a gap of 3 to 10 minutes after each, for four hours.
				var at = 10f + 80f * random.NextSingle();
				while ( at < 4 * 3600f )
				{
					var duration = 180f + 300f * random.NextSingle();
					var u = random.NextSingle();
					showers.Add( new Shower( at, duration, 4f + 36f * u * u ) );
					at += duration + 180f + 420f * random.NextSingle();
				}
				list = showers.ToArray();
				Showers[seed] = list;
				return list;
			}
		}

		private static float Hash01( int seed, int salt )
		{
			var h = (uint)seed * 0x9E3779B1u ^ (uint)salt * 0x85EBCA77u;
			h ^= h >> 15;
			h *= 0x2C1B3C6Du;
			h ^= h >> 12;
			return (h & 0xFFFFFF) / 16777216f;
		}
	}
}
