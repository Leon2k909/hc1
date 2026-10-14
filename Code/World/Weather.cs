namespace Facepunch;

public enum WeatherKind
{
	Clear,
	/// <summary> Drizzle: fine drops under 0.5 mm, 0.2-0.8 mm/h. </summary>
	Drizzle,
	/// <summary> Steady rain from a passing stratiform deck: 2-6 mm/h. </summary>
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

	/// <summary> The share of outdoor matches that have rain, distributed across each map's matches. </summary>
	public const float RainChance = 0.25f;

	private static readonly Dictionary<string, RainCycle> MatchRain = new( StringComparer.OrdinalIgnoreCase );

	// Sample without replacement: keep the same rain share without arbitrarily long clear streaks.
	private sealed class RainCycle
	{
		private int _remaining;
		private bool _rainRemaining;

		public bool Next( System.Random random )
		{
			if ( _remaining == 0 )
			{
				_remaining = (int)(1f / RainChance);
				_rainRemaining = true;
			}
			var rain = _rainRemaining && random.Next( _remaining ) == 0;
			_remaining--;
			if ( rain ) _rainRemaining = false;
			return rain;
		}
	}

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

	/// <summary> The cloud front's progress, including its approach before the first rain and its clearing afterwards. </summary>
	public float OvercastAmount => Kind == WeatherKind.Clear ? 0f : ForcedRate >= 0f ? 1f : Schedule.OvercastAt( Kind, Seed, Elapsed );

	/// <summary> Slow changes in fair-weather cloud cover, shared by every client. </summary>
	public float CloudCover => Schedule.CloudCoverAt( Seed, Elapsed );

	private bool _rolled;
	private TimeSince _sinceStart;
	private RainView _view;

	/// <summary> The rain on the grass (mm), drying with fine grass's one-hour timelag. </summary>
	private float _wetMm;

	private Vector3? _calmWind;
	private float _calmGust;
	private WeatherKind? _windKind;

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
		if ( !IsProxy && !_rolled && ((_sinceStart > 1f && MapsLoaded()) || _sinceStart > MapLoadTimeout) )
			Roll();

		if ( !IsProxy && _rolled )
		{
			var windKind = OvercastAmount > 0.1f ? Kind : WeatherKind.Clear;
			if ( _windKind != windKind ) SetWind( windKind );
		}

		// A clear match still has slowly changing cloud cover and daylight. Rain effects are created only when needed.
		if ( !Application.IsDedicatedServer && !_view.IsValid() && (IsRaining || HasSky()) )
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
	private bool HasSky() => Scene.GetAllComponents<SkyBox2D>().Any( sky => sky.Active )
		|| Scene.SceneWorld.SceneObjects.OfType<SceneSkyBox>().Any();

	private void Roll()
	{
		_rolled = true;
		Seed = Random.Shared.Next();
		Elapsed = 0;
		var hasSky = HasSky();
		var map = Scene.Source?.ResourcePath ?? Scene.Name;
		if ( !MatchRain.TryGetValue( map, out var cycle ) ) MatchRain[map] = cycle = new RainCycle();
		if ( !hasSky || !cycle.Next( Random.Shared ) )
		{
			Set( WeatherKind.Clear, -1f );
			Log.Info( $"Weather: Clear ({map})" );
			return;
		}

		// Of the rainy matches: a quarter drizzle, two fifths steady rain, the rest showers.
		var pick = Random.Shared.NextSingle();
		Set( pick < 0.25f ? WeatherKind.Drizzle : pick < 0.65f ? WeatherKind.Steady : WeatherKind.Showers, -1f );

		// The grass is as wet as the rain before the match left it.
		_wetMm = 0f;
		for ( var t = -7200f; t < 0f; t += 60f )
			_wetMm = (_wetMm + Schedule.RateAt( Kind, Seed, t + 30f ) / 3600f * 60f) * MathF.Exp( -60f / 3600f );
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
		_windKind = kind;

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

		/// <summary>
		/// The rate at <paramref name="time"/> seconds into the match. It's rained before the match too (negative times),
		/// so the ground is as wet as that left it (<see cref="RainPuddles"/>). Half the drizzle and steady fronts are
		/// already present; the others arrive during play. Showers have often had one in the last hour.
		/// </summary>
		public static float RateAt( WeatherKind kind, int seed, float time ) => kind switch
		{
			// Drizzle and stratiform rain come and go slowly, with the deck's own lumps.
			WeatherKind.Drizzle => MathX.Lerp( 0.2f, 0.8f, Hash01( seed, 1 ) ) * Wander( seed, time, 0.3f ) * FrontAt( seed, time ),
			WeatherKind.Steady => MathX.Lerp( 2f, 6f, Hash01( seed, 2 ) ) * Wander( seed, time, 0.35f ) * FrontAt( seed, time ),
			WeatherKind.Showers => ShowerRate( seed, time ),
			_ => 0f,
		};

		/// <summary> Half of fronts are already here; the others arrive 1.5-5 minutes into the match. </summary>
		public static float RainStart( int seed ) => Hash01( seed, 11 ) < 0.5f
			? -MathX.Lerp( 600f, 7200f, Hash01( seed, 6 ) )
			: MathX.Lerp( 90f, 300f, Hash01( seed, 12 ) );

		private static float RainEnd( int seed ) => MathX.Lerp( 480f, 840f, Hash01( seed, 13 ) );

		/// <summary> Rain builds over two minutes and eases off over three, after 8-14 minutes of match time. </summary>
		private static float FrontAt( int seed, float time ) =>
			RainView.SmoothStep( RainStart( seed ), RainStart( seed ) + 120f, time )
			* (1f - RainView.SmoothStep( RainEnd( seed ), RainEnd( seed ) + 180f, time ));

		public static float OvercastAt( WeatherKind kind, int seed, float time ) => kind switch
		{
			WeatherKind.Drizzle or WeatherKind.Steady =>
				RainView.SmoothStep( RainStart( seed ) - 120f, RainStart( seed ) + 30f, time )
				* (1f - RainView.SmoothStep( RainEnd( seed ) + 180f, RainEnd( seed ) + 300f, time )),
			WeatherKind.Showers => 1f,
			_ => 0f,
		};

		/// <summary> A smooth change between cloud banks over 5-8 minutes, with no steps at interval boundaries. </summary>
		public static float CloudCoverAt( int seed, float time )
		{
			var period = MathX.Lerp( 300f, 480f, Hash01( seed, 14 ) );
			var phase = time / period;
			var interval = (int)MathF.Floor( phase );
			var k = RainView.SmoothStep( 0f, 1f, phase - interval );
			return MathX.Lerp( 0.15f, 0.75f, MathX.Lerp( Hash01( seed, 100 + interval ), Hash01( seed, 101 + interval ), k ) );
		}

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

				// Seven times in ten, one went over in the hour before the match, ending 5 minutes to an hour before it.
				// It has its own random numbers, so the match's showers are the same with or without it.
				var before = new System.Random( seed ^ 0x5BD1E995 );
				if ( before.NextSingle() < 0.7f )
				{
					var end = -(300f + 3300f * before.NextSingle());
					var length = 180f + 300f * before.NextSingle();
					var v = before.NextSingle();
					showers.Add( new Shower( end - length, length, 4f + 36f * v * v ) );
				}

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

		/// <summary>
		/// A lightning flash: when (seconds into the match), how far off (m), its bearing in the map's plan (radians from
		/// +X), whether it stayed in the cloud, and a number for its strokes and its thunder's take.
		/// </summary>
		public readonly record struct Strike( float Time, float Distance, float Bearing, bool IsCloud, int Salt );

		private static readonly Dictionary<(WeatherKind, int), Strike[]> StrikeLists = new();

		/// <summary> Past this, thunder isn't heard (it's refracted up over the listener); the flash still shows. </summary>
		public const float AudibleRange = 18000f;

		/// <summary>
		/// The match's lightning, in time order. A shower that peaks over 12 mm/h is a thunderstorm's: its cell drifts past
		/// at 6-14 m/s with the others, closest 0.5-6 km off when the rain's heaviest, and flashes from 5 minutes before
		/// its rain to 3 after, most in its mature middle, half a flash to three a minute for the strongest. Three in five
		/// flashes stay in the cloud. One steady rain in three has embedded storms far off, with a rumble every 3-6 minutes.
		/// Drizzle has none.
		/// </summary>
		public static Strike[] Strikes( WeatherKind kind, int seed )
		{
			lock ( StrikeLists )
			{
				if ( StrikeLists.TryGetValue( (kind, seed), out var cached ) ) return cached;

				var random = new System.Random( seed ^ 0x2545F491 );
				var strikes = new List<Strike>();
				var steering = Hash01( seed, 8 ) * MathF.Tau;

				if ( kind == WeatherKind.Showers )
				{
					foreach ( var shower in ShowersOf( seed ) )
					{
						if ( shower.Peak <= 12f ) continue;
						var perSecond = MathX.Lerp( 0.5f, 3f, (shower.Peak - 12f) / 28f ) / 60f;
						var heading = steering + (random.NextSingle() - 0.5f) * 1.0f;
						var speed = 6f + 8f * random.NextSingle();
						var miss = (500f + 5500f * random.NextSingle() * random.NextSingle()) * (random.NextSingle() < 0.5f ? -1f : 1f);
						var dir = new Vector2( MathF.Cos( heading ), MathF.Sin( heading ) );
						var side = new Vector2( -dir.y, dir.x );
						var from = shower.Start - 300f;
						var to = shower.Start + shower.Duration + 180f;
						var mid = shower.Start + shower.Duration * 0.5f;

						// A Poisson stream at the peak rate, thinned to a bell over the cell's life.
						for ( var t = from; ; )
						{
							t += -MathF.Log( 1f - 0.999f * random.NextSingle() ) / perSecond;
							if ( t > to ) break;
							var x = (t - mid) / (0.5f * (to - from));
							var keep = random.NextSingle() < MathF.Exp( -2.5f * x * x );
							var r = 1800f * MathF.Sqrt( -2f * MathF.Log( 1f - 0.999f * random.NextSingle() ) );
							var a = random.NextSingle() * MathF.Tau;
							var cloud = random.NextSingle() < 0.6f;
							var salt = random.Next();
							if ( !keep ) continue;

							var at = dir * (speed * (t - mid)) + side * miss + new Vector2( MathF.Cos( a ), MathF.Sin( a ) ) * r;
							strikes.Add( new Strike( t, MathF.Max( at.Length, 150f ), MathF.Atan2( at.y, at.x ), cloud, salt ) );
						}
					}
				}
				else if ( kind == WeatherKind.Steady && Hash01( seed, 7 ) < 0.3f )
				{
					for ( var t = 60f + 120f * random.NextSingle(); t < 4 * 3600f; t += 180f + 180f * random.NextSingle() )
					{
						if ( FrontAt( seed, t ) <= 0f ) continue;
						var bearing = steering + (random.NextSingle() - 0.5f) * 2f;
						strikes.Add( new Strike( t, 6000f + 9000f * random.NextSingle(), bearing, random.NextSingle() < 0.8f, random.Next() ) );
					}
				}

				strikes.Sort( ( a, b ) => a.Time.CompareTo( b.Time ) );
				var list = strikes.ToArray();
				StrikeLists[(kind, seed)] = list;
				return list;
			}
		}

		/// <summary>
		/// How bright a flash is <paramref name="t"/> seconds after it began, against a ground strike's 2 km off. A ground
		/// flash is 2-5 return strokes 35-85 ms apart, each a blink that's gone in a few tens of milliseconds, with the
		/// channel glowing between them. A flash in the cloud lights it from inside: dimmer, softer pulses over half a
		/// second. Under the cloud the light comes from all round, so it falls off slower than a point's would.
		/// </summary>
		public static float FlashAt( in Strike strike, float t )
		{
			if ( t < 0f || t > 1.2f ) return 0f;
			var light = 0f;
			var at = 0f;
			if ( strike.IsCloud )
			{
				var pulses = 3 + (int)(Hash01( strike.Salt, 1 ) * 4f);
				for ( var i = 0; i < pulses && at <= t; i++ )
				{
					var rise = Math.Clamp( (t - at) / 0.02f, 0f, 1f );
					light += (0.5f + 0.5f * Hash01( strike.Salt, 10 + i )) * rise * MathF.Exp( -(t - at) / 0.07f );
					at += 0.06f + 0.12f * Hash01( strike.Salt, 20 + i );
				}
				light *= 0.45f;
			}
			else
			{
				var strokes = 2 + (int)(Hash01( strike.Salt, 1 ) * 4f);
				for ( var i = 0; i < strokes && at <= t; i++ )
				{
					light += (i == 0 ? 1f : 0.6f + 0.3f * Hash01( strike.Salt, 10 + i )) * MathF.Exp( -(t - at) / 0.025f );
					at += 0.035f + 0.05f * Hash01( strike.Salt, 20 + i );
				}
				// The continuing current between and after the strokes.
				light += 0.2f * MathF.Exp( -t / 0.2f );
			}

			var reach = Math.Clamp( MathF.Pow( 2000f / MathF.Max( strike.Distance, 100f ), 1.5f ), 0.04f, 1.5f );
			return light * reach;
		}

		internal static float Hash01( int seed, int salt )
		{
			var h = (uint)seed * 0x9E3779B1u ^ (uint)salt * 0x85EBCA77u;
			h ^= h >> 15;
			h *= 0x2C1B3C6Du;
			h ^= h >> 12;
			return (h & 0xFFFFFF) / 16777216f;
		}
	}
}
