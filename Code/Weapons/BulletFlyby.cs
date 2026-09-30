namespace Facepunch;

/// <summary>
/// What a bullet sounds like to someone it passes: a supersonic round's crack, a subsonic one's whizz, and what it
/// strikes. Players' and bots' shots alike, heard from the listener's own camera.
/// <para>
/// A supersonic bullet drags a cone of shock (a Mach cone) behind it. Someone off its path hears it once, as the cone
/// sweeps over them: an N-wave, a jump in pressure that falls away linearly to as far below the air's pressure and jumps
/// back, a few hundred microseconds long. It left the path where the cone through them meets it, a little before the
/// point nearest them, <c>miss / sqrt(M^2 - 1)</c> back at the Mach number M the bullet had there, so it seems to come
/// from there, not from the gun (<see cref="TryShock"/>). It comes before the gun's report when the listener is far
/// enough downrange, and the gap grows with the range: the crack-thump soldiers judge a shooter's distance by. The
/// report travels at the speed of sound too (<see cref="GunshotAudio"/>).
/// </para>
/// <para>
/// The wave's strength and length are Whitham's (1952) far-field N-wave, which measurements of small-arms cracks follow
/// (it's what shot-localising systems use): an overpressure of <c>0.53 p0 (M^2 - 1)^(1/8) d / (b^(3/4) l^(1/4))</c>
/// lasting <c>1.82 M b^(1/4) d / (c (M^2 - 1)^(3/8) l^(1/4))</c>, for a bullet of diameter d and length l passing b
/// away. An M855 at Mach 2.5 a metre away is ~970 Pa (154 dB peak) for 100 us; a 9 mm round, fatter and slower, is
/// louder and twice as long, a duller snap. Past a metre the pressure falls as b^(-3/4) and the wave lengthens as
/// b^(1/4). The bullet's speed along its path is its load's (<see cref="Ballistics"/>), so a crack weakens and lengthens
/// downrange, and past where the round drops under ~Mach 1.03 there's none: a subsonic round (the .45s, 9x18) only
/// whizzes, heard within a few metres (<see cref="PlayWhizz"/>).
/// </para>
/// <para>
/// The ground, a ceiling and the nearest two walls throw a second crack each (<see cref="PlayReflection"/>): the crack
/// heard at the listener's mirror image in each, from the mirror image of where it left, if the wave really reaches
/// the surface there. Standing on hard ground that's the "double crack" a few milliseconds apart; grass and earth give
/// a weaker, duller one.
/// </para>
/// <para>
/// The sounds are made here, not recorded: each N-wave is drawn 16 times over the output's rate, with a front that's
/// sharp, firm, spiked or rounded (turbulence on the way reshapes it, the rounded more often the further it came), and
/// band-limited to 20 kHz (<see cref="MakeCrack"/>). They're cached as clips by length, in 20% steps.
/// </para>
/// </summary>
public static class BulletFlyby
{
	/// <summary> The speed of sound, in units a second. </summary>
	public const float SoundSpeed = Ballistics.SpeedOfSound * Ballistics.UnitsPerMeter;

	private const float Metre = Ballistics.UnitsPerMeter;
	private const float SpeedOfSound = Ballistics.SpeedOfSound;

	/// <summary> The air's pressure, in Pa (sea level, as <see cref="Ballistics"/>'s air). </summary>
	private const float AmbientPressure = 101325f;

	/// <summary>
	/// The pressure a full-scale sample stands for, in Pa. The guns' shots are mastered so their loudest 100 ms is about
	/// -5 dB (K-weighted) for ~137 dB(A) at the shooter's ear, which puts a full-scale sine at ~142 dB SPL: 252 Pa rms,
	/// 356 Pa at its peak.
	/// </summary>
	private const float FullScalePascals = 356f;

	/// <summary> The loudest a crack's peak plays, as a share of full scale. Closer than a few metres a real one is louder. </summary>
	private const float MaxPeak = 1f;

	/// <summary> How far off its path a crack is still worked out, in metres (~30 Pa for a rifle round there). </summary>
	private const float MaxCrackMiss = 100f;

	/// <summary> Closer than this (m) the far-field sums don't hold, so the crack is taken at this distance. </summary>
	private const float MinCrackMiss = 0.15f;

	/// <summary> Under this Mach number the cone stands so steep and weak that it's no crack. </summary>
	private const float MinMach = 1.03f;

	/// <summary> How close a subsonic round passes to be heard, in metres. </summary>
	private const float WhizzReach = 6f;

	/// <summary> A .45 ACP ball round's whizz at a metre, as a share of full scale at its peak. </summary>
	private const float WhizzLevel = 0.05f;

	/// <summary> How far from the listener a bullet's strike is played, in units (~76 m); past it the event is silent. </summary>
	private const float ImpactReach = 3000f;

	private const int SampleRate = 44100;

	/// <summary> Clips are normalised to this peak. </summary>
	private const float Headroom = 0.9f;

	/// <summary> The shortest crack clip (s); each next one is <see cref="CrackStep"/> times longer. </summary>
	private const float ShortestCrack = 40e-6f;
	private const float CrackStep = 1.2f;
	private const int CrackSteps = 21;

	/// <summary> The whizz clips' bullet speeds (Mach) and misses (m). </summary>
	private static readonly float[] WhizzMachs = { 0.75f, 0.9f };
	private static readonly float[] WhizzMisses = { 0.5f, 1f, 2f, 4f };

	/// <summary> How a crack's shocks are shaped when it arrives. </summary>
	private enum Front
	{
		/// <summary> Shocks a few microseconds thick, as in still air. </summary>
		Sharp,
		Firm,
		/// <summary> Turbulence focusing the shocks: a spike on each. </summary>
		Spiked,
		/// <summary> Turbulence spreading them. </summary>
		Rounded,
		/// <summary> Off grass or earth, which soak up the top of it. </summary>
		Soft,
	}

	/// <summary> A made sound: the clip, where its wave arrives in it, and its peak before it was normalised. </summary>
	private sealed class Clip
	{
		public SoundFile File;

		/// <summary> A crack's band-limited peak for a unit N-wave. A whizz's is 1: its level is its peak. </summary>
		public float Unit;

		/// <summary> Seconds into the clip that a crack's front, or a whizz's closest pass, arrives. </summary>
		public float Lead;
	}

	private static readonly Dictionary<int, Clip> Clips = new();

	/// <summary> A bullet's straight path, from the muzzle to where it stopped. </summary>
	private readonly struct Flight
	{
		public readonly Ballistics.Trajectory Trajectory;
		public readonly Vector3 Origin;
		public readonly Vector3 Direction;

		/// <summary> How far it went, in metres. </summary>
		public readonly float Range;

		/// <summary> The bullet's diameter and length, in metres. </summary>
		public readonly float Diameter;
		public readonly float Length;

		public Flight( Shootable gun, Vector3 origin, Vector3 end )
		{
			Trajectory = Ballistics.Get( gun.DragFunction, gun.MuzzleVelocity, gun.BallisticCoefficient );
			Origin = origin;
			var path = end - origin;
			Range = path.Length / Metre;
			Direction = path.Normal;
			// An M855 if the gun doesn't say.
			Diameter = (gun.BulletDiameter > 0f ? gun.BulletDiameter : 5.7f) / 1000f;
			Length = (gun.BulletLength > 0f ? gun.BulletLength : 23f) / 1000f;
		}

		public Vector3 At( float metres ) => Origin + Direction * (metres * Metre);
	}

	/// <summary> The crack that reaches one listener. </summary>
	private struct Shock
	{
		/// <summary> Where on the path it left. </summary>
		public Vector3 Emitted;

		/// <summary> When it arrives, in seconds after the shot. </summary>
		public float Arrival;

		/// <summary> Its peak overpressure (Pa) and length (s). </summary>
		public float Pressure;
		public float Duration;

		/// <summary> How far off the path the listener is, in metres. </summary>
		public float Miss;
	}

	/// <summary> Something a crack bounces off: a plane through <see cref="Point"/>. </summary>
	private sealed class Reflector
	{
		public Vector3 Point;
		public Vector3 Normal;

		/// <summary> The share of the wave's pressure it sends back. </summary>
		public float Reflectance;

		/// <summary> Grass, earth or cloth, which take the top off it. </summary>
		public bool Soft;
	}

	private static Reflector[] _reflectors;
	private static Vector3 _probedAt;
	private static RealTimeSince _sinceProbed;

	/// <summary>
	/// A bullet fired now from <paramref name="gun"/> at <paramref name="origin"/>, that stopped at
	/// <paramref name="end"/>: its crack or whizz for the listener when <paramref name="flyby"/>, and, when
	/// <paramref name="impact"/>, what it strikes at the end, once it's got there and the sound has come back.
	/// <paramref name="reflections"/> adds the cracks off the ground and walls (one bullet of a shotgun's is enough).
	/// </summary>
	public static void Pass( Shootable gun, Vector3 origin, Vector3 end, bool flyby, bool impact, bool reflections )
	{
		if ( Application.IsHeadless || !gun.IsValid() || gun.MuzzleVelocity <= 0f || gun.BallisticCoefficient <= 0f )
			return;

		var camera = Game.ActiveScene?.Camera;
		if ( !camera.IsValid() || origin.Distance( end ) < 1f )
			return;

		var scene = camera.Scene;
		var listener = camera.WorldPosition;
		var flight = new Flight( gun, origin, end );

		if ( flyby )
		{
			if ( TryShock( flight, listener, out var shock ) )
			{
				PlayCrack( shock, shock.Emitted, 1f, PickFront( shock.Miss ), true );
				if ( reflections )
				{
					foreach ( var reflector in Reflectors( scene, listener ) )
						PlayReflection( scene, flight, listener, reflector );
				}
			}
			else
			{
				PlayWhizz( flight, listener );
			}
		}

		if ( impact )
			PlayImpact( scene, flight, end, listener );
	}

	/// <summary>
	/// How long after the shot a bullet from <paramref name="gun"/> takes to fly from <paramref name="origin"/> to
	/// <paramref name="point"/>, in seconds.
	/// </summary>
	public static float TimeOfFlight( Shootable gun, Vector3 origin, Vector3 point )
	{
		if ( !gun.IsValid() || gun.MuzzleVelocity <= 0f || gun.BallisticCoefficient <= 0f )
			return 0f;

		return Ballistics.Get( gun.DragFunction, gun.MuzzleVelocity, gun.BallisticCoefficient ).TimeAt( origin.Distance( point ) / Metre );
	}

	/// <summary>
	/// The crack that reaches <paramref name="listener"/>, if one does. It left the path at x, where
	/// <c>x + miss / sqrt(M(x)^2 - 1)</c> is how far along the path the listener is. That grows with x (the bullet slows),
	/// so it's found by halving. None if the listener is beside or behind the gun, where the cone hasn't formed, if that
	/// point is past where the bullet stopped, or if the bullet is under <see cref="MinMach"/> there.
	/// </summary>
	private static bool TryShock( in Flight flight, Vector3 listener, out Shock shock )
	{
		shock = default;
		var offset = (listener - flight.Origin) / Metre;
		var along = Vector3.Dot( offset, flight.Direction );
		var miss = (offset - flight.Direction * along).Length;
		if ( miss > MaxCrackMiss || along <= 0f )
			return false;

		var trajectory = flight.Trajectory;
		var b = MathF.Max( miss, MinCrackMiss );
		float Behind( float x )
		{
			var mach = trajectory.SpeedAt( x ) / SpeedOfSound;
			return mach <= MinMach ? float.MaxValue : x + b / MathF.Sqrt( mach * mach - 1f ) - along;
		}

		var high = MathF.Min( along, flight.Range );
		if ( Behind( 0f ) > 0f || Behind( high ) < 0f )
			return false;

		var low = 0f;
		for ( var i = 0; i < 24; i++ )
		{
			var middle = (low + high) * 0.5f;
			if ( Behind( middle ) < 0f ) low = middle;
			else high = middle;
		}

		var x = low;
		var m = MathF.Max( trajectory.SpeedAt( x ) / SpeedOfSound, MinMach );
		var m2 = m * m - 1f;
		var lengthRoot = MathF.Pow( flight.Length, 0.25f );

		shock.Emitted = flight.At( x );
		shock.Arrival = trajectory.TimeAt( x ) + shock.Emitted.Distance( listener ) / SoundSpeed;
		shock.Pressure = 0.53f * AmbientPressure * MathF.Pow( m2, 0.125f ) * flight.Diameter / (MathF.Pow( b, 0.75f ) * lengthRoot);
		shock.Duration = 1.82f * m * MathF.Pow( b, 0.25f ) * flight.Diameter / (SpeedOfSound * MathF.Pow( m2, 0.375f ) * lengthRoot);
		shock.Miss = miss;
		return true;
	}

	/// <summary> Turbulence rounds a crack's fronts more often the further off its path it's heard. </summary>
	private static Front PickFront( float miss )
	{
		var rounded = Math.Clamp( miss / 60f, 0.1f, 0.6f );
		var roll = Game.Random.Float( 0f, 1f );
		if ( roll < rounded )
			return Front.Rounded;

		roll = (roll - rounded) / (1f - rounded);
		return roll < 0.4f ? Front.Sharp : roll < 0.75f ? Front.Firm : Front.Spiked;
	}

	/// <summary> Plays <paramref name="shock"/> from <paramref name="from"/>, its pressure scaled by <paramref name="gain"/>. </summary>
	private static void PlayCrack( in Shock shock, Vector3 from, float gain, Front front, bool direct )
	{
		var index = Math.Clamp( (int)MathF.Round( MathF.Log( shock.Duration / ShortestCrack ) / MathF.Log( CrackStep ) ), 0, CrackSteps - 1 );
		var clip = MakeCrack( index, front, Game.Random.Int( 0, 1 ) );
		if ( clip is null )
			return;

		// The pressure as a share of full scale, capped. The level is set here, so the engine's distance falloff is off,
		// but the air still takes the top off a far one and a wall between muffles it.
		var volume = MathF.Min( gain * shock.Pressure / FullScalePascals * clip.Unit, MaxPeak ) / Headroom;
		if ( volume < 0.001f )
			return;

		var handle = Sound.PlayFile( clip.File, volume, pitch: 1f, delay: MathF.Max( 0f, shock.Arrival - clip.Lead ) );
		if ( !handle.IsValid() )
			return;

		handle.Position = from;
		handle.SpacialBlend = 1f;
		handle.DistanceAttenuation = false;
		handle.AirAbsorption = true;
		// A reflection's image is behind its surface, so the engine would muffle it: its way was checked instead.
		handle.OcclusionEnabled = direct;
		handle.ReverbEnabled = true;
	}

	/// <summary>
	/// The crack off <paramref name="reflector"/>: the one that reaches the listener's mirror image in it, heard from the
	/// mirror image of where it left the path. Only if the wave reaches the surface on its way (nothing in between) and
	/// the surface is really there, where the listener sees it.
	/// </summary>
	private static void PlayReflection( Scene scene, in Flight flight, Vector3 listener, Reflector reflector )
	{
		var image = Mirror( listener, reflector );
		if ( !TryShock( flight, image, out var shock ) )
			return;

		var toImage = image - shock.Emitted;
		var across = Vector3.Dot( toImage, reflector.Normal );
		if ( MathF.Abs( across ) < 0.001f )
			return;

		var share = Vector3.Dot( reflector.Point - shock.Emitted, reflector.Normal ) / across;
		if ( share <= 0f || share >= 1f )
			return;

		var bounce = shock.Emitted + toImage * share;
		if ( Solid( scene, shock.Emitted, bounce - toImage.Normal * 4f ).Run().Hit )
			return;

		var seen = Solid( scene, listener, bounce + (bounce - listener).Normal * 8f ).Run();
		if ( !seen.Hit || seen.EndPosition.Distance( bounce ) > 16f )
			return;

		PlayCrack( shock, Mirror( shock.Emitted, reflector ), reflector.Reflectance,
			reflector.Soft ? Front.Soft : PickFront( shock.Miss ), false );
	}

	private static Vector3 Mirror( Vector3 point, Reflector reflector ) =>
		point - 2f * Vector3.Dot( point - reflector.Point, reflector.Normal ) * reflector.Normal;

	/// <summary>
	/// The surfaces round the listener that throw cracks back: the ground or floor under them, a ceiling over them, and
	/// the nearest two walls (of eight probes round them, 30 m out). Kept for a quarter of a second while they stay put.
	/// </summary>
	private static Reflector[] Reflectors( Scene scene, Vector3 listener )
	{
		if ( _reflectors is not null && _sinceProbed < 0.25f && _probedAt.Distance( listener ) < 24f )
			return _reflectors;

		var found = new List<Reflector>( 4 );
		if ( Surface( scene, listener, Vector3.Down, 2000f ) is { } ground && ground.Normal.z > 0.7f )
			found.Add( ground );
		if ( Surface( scene, listener, Vector3.Up, 1200f ) is { } ceiling && ceiling.Normal.z < -0.7f )
			found.Add( ceiling );

		var walls = new List<(Reflector Wall, float Distance)>();
		for ( var i = 0; i < 8; i++ )
		{
			var angle = i * MathF.PI / 4f;
			var direction = new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f );
			if ( Surface( scene, listener, direction, 1200f ) is { } wall && MathF.Abs( wall.Normal.z ) < 0.35f )
				walls.Add( (wall, Vector3.Dot( listener - wall.Point, wall.Normal )) );
		}

		var kept = 0;
		foreach ( var (wall, _) in walls.OrderBy( x => x.Distance ) )
		{
			if ( kept == 2 )
				break;

			// Probes that found the same wall.
			if ( found.Any( x => Vector3.Dot( x.Normal, wall.Normal ) > 0.87f ) )
				continue;

			found.Add( wall );
			kept++;
		}

		_reflectors = found.ToArray();
		_probedAt = listener;
		_sinceProbed = 0f;
		return _reflectors;
	}

	/// <summary> The surface <paramref name="reach"/> along <paramref name="direction"/> from <paramref name="from"/>, if any. </summary>
	private static Reflector Surface( Scene scene, Vector3 from, Vector3 direction, float reach )
	{
		var tr = Solid( scene, from, from + direction * reach ).Run();
		if ( !tr.Hit || tr.StartedSolid )
			return null;

		// Grass and loose earth are porous, and take a crack's highs; hard ground, walls and glass send nearly all of it back.
		var material = WorldSounds.Classify( WorldSounds.SurfaceAt( tr ) );
		var reflectance = material switch
		{
			WorldSounds.Material.Grass => 0.45f,
			WorldSounds.Material.Dirt => 0.6f,
			WorldSounds.Material.Fabric => 0.3f,
			_ => 0.9f,
		};

		return new Reflector
		{
			Point = tr.EndPosition,
			Normal = tr.Normal,
			Reflectance = reflectance,
			Soft = reflectance < 0.7f,
		};
	}

	/// <summary> A trace through the air: people, triggers, clips and grenades don't stop sound's way. </summary>
	private static SceneTrace Solid( Scene scene, Vector3 from, Vector3 to ) => scene.Trace.Ray( from, to )
		.WithoutTags( "trigger", "playerclip", "movement", "player", "ragdoll", "enemy", "grenade" );

	/// <summary>
	/// A subsonic round passing within <see cref="WhizzReach"/>: the rush of its wake, which rises in pitch as it comes
	/// and falls as it goes (Doppler), played from its closest point. Its flow noise grows with the speed cubed and the
	/// diameter, and falls with the distance.
	/// </summary>
	private static void PlayWhizz( in Flight flight, Vector3 listener )
	{
		var offset = (listener - flight.Origin) / Metre;
		var along = Vector3.Dot( offset, flight.Direction );
		if ( along <= 0f || along > flight.Range )
			return;

		var miss = (offset - flight.Direction * along).Length;
		if ( miss > WhizzReach )
			return;

		var speed = flight.Trajectory.SpeedAt( along );
		var mach = speed / SpeedOfSound;
		if ( mach >= 1f || speed < 60f )
			return;

		var machIndex = mach < (WhizzMachs[0] + WhizzMachs[1]) * 0.5f ? 0 : 1;
		var missIndex = 0;
		for ( var i = 1; i < WhizzMisses.Length; i++ )
		{
			if ( MathF.Abs( MathF.Log( miss / WhizzMisses[i] ) ) < MathF.Abs( MathF.Log( miss / WhizzMisses[missIndex] ) ) )
				missIndex = i;
		}

		var clip = MakeWhizz( machIndex, missIndex, Game.Random.Int( 0, 1 ) );
		if ( clip is null )
			return;

		var level = WhizzLevel * MathF.Pow( speed / 255f, 3f ) * (flight.Diameter / 0.01148f) / MathF.Max( miss, 0.3f );
		var volume = MathF.Min( level, 0.4f ) / Headroom;
		var arrival = flight.Trajectory.TimeAt( along ) + miss / SpeedOfSound;

		var handle = Sound.PlayFile( clip.File, volume, pitch: 1f, delay: MathF.Max( 0f, arrival - clip.Lead ) );
		if ( !handle.IsValid() )
			return;

		handle.Position = flight.At( along );
		handle.SpacialBlend = 1f;
		handle.DistanceAttenuation = false;
		handle.AirAbsorption = true;
		handle.OcclusionEnabled = true;
		handle.ReverbEnabled = true;
	}

	/// <summary>
	/// What the bullet strikes at <paramref name="end"/>, found by a short trace across it, heard once the bullet has
	/// got there and the sound has come back.
	/// </summary>
	private static void PlayImpact( Scene scene, in Flight flight, Vector3 end, Vector3 listener )
	{
		if ( end.Distance( listener ) > ImpactReach )
			return;

		var tr = scene.Trace.Ray( end - flight.Direction * 12f, end + flight.Direction * 12f )
			.UseHitboxes()
			.WithoutTags( "trigger", "playerclip", "movement" )
			.Run();
		if ( !tr.Hit || WorldSounds.BulletImpact( tr, tr.GetImpactSurface() ) is not { } sound )
			return;

		var delay = flight.Trajectory.TimeAt( flight.Origin.Distance( tr.EndPosition ) / Metre )
			+ tr.EndPosition.Distance( listener ) / SoundSpeed;
		GunshotAudio.PlayDelayed( sound, tr.EndPosition, delay );
	}

	/// <summary>
	/// A crack clip: an N-wave <see cref="ShortestCrack"/> x <see cref="CrackStep"/>^<paramref name="index"/> long, with
	/// its shocks shaped as <paramref name="front"/>, drawn at 16 times the output's rate, band-limited to 20 kHz and
	/// normalised. <paramref name="take"/> picks one of two draws, whose shocks fall at other points between samples.
	/// </summary>
	private static Clip MakeCrack( int index, Front front, int take )
	{
		var key = ((index * 8 + (int)front) * 2 + take) * 2;
		if ( Clips.TryGetValue( key, out var made ) && made.File.IsValid() )
			return made;

		const int factor = 16;
		var rate = (float)SampleRate * factor;
		var random = new Random( key * 7919 + 17 );
		var duration = ShortestCrack * MathF.Pow( CrackStep, index );
		var (rise, spike) = front switch
		{
			Front.Sharp => (2e-6f, 0f),
			Front.Firm => (8e-6f, 0.15f),
			Front.Spiked => (3e-6f, 0.5f),
			Front.Rounded => (25e-6f, 0f),
			_ => (90e-6f, 0f),
		};

		// The filter's run-in, then the front a fraction of a sample later in each take.
		var lead = 0.001f + (float)random.NextDouble() / SampleRate;
		var wave = new float[(int)((lead + duration + 0.002f) * rate)];
		var start = lead * rate;
		var end = start + duration * rate;
		var decay = 8e-6f * rate;
		for ( var i = 0; i < wave.Length; i++ )
		{
			if ( i >= start && i < end )
				wave[i] = 1f - 2f * (i - start) / (end - start);

			// Each shock overshoots and settles within ~10 us.
			if ( spike > 0f && i >= start )
				wave[i] += spike * MathF.Exp( -(i - start) / decay );
			if ( spike > 0f && i >= end )
				wave[i] += spike * MathF.Exp( -(i - end) / decay );
		}

		wave = Smooth( wave, rise * rate );
		var clip = Store( $"hc1/flyby/crack_{index:00}_{front.ToString().ToLowerInvariant()}_{take}", Decimate( wave, factor ), lead );
		if ( clip is not null )
			Clips[key] = clip;
		return clip;
	}

	/// <summary>
	/// A whizz clip: a round at <see cref="WhizzMachs"/>[<paramref name="machIndex"/>] passing
	/// <see cref="WhizzMisses"/>[<paramref name="missIndex"/>] away. Its wake's rush (noise a couple of octaves wide round
	/// its shedding frequency, 0.2 v / d for a 10 mm bullet) is heard as it arrives: each moment of it at the time it
	/// was made plus its way to the listener, so the approach comes squeezed up in pitch and the going stretched down,
	/// louder coming than going.
	/// </summary>
	private static Clip MakeWhizz( int machIndex, int missIndex, int take )
	{
		var key = ((machIndex * 4 + missIndex) * 2 + take) * 2 + 1;
		if ( Clips.TryGetValue( key, out var made ) && made.File.IsValid() )
			return made;

		const int factor = 4;
		var rate = (float)SampleRate * factor;
		var random = new Random( key * 7919 + 29 );
		var speed = WhizzMachs[machIndex] * SpeedOfSound;
		var miss = WhizzMisses[missIndex];

		// Its own time: 6 misses' flight before the closest point to 10 after.
		var first = -6f * miss / speed;
		var last = 10f * miss / speed;
		var noise = new float[(int)((last - first) * rate) + 2];
		for ( var i = 0; i < noise.Length; i++ )
			noise[i] = (float)(random.NextDouble() + random.NextDouble() + random.NextDouble() - 1.5) * 2f;
		noise = BandPass( noise, 0.2f * speed / 0.010f, 0.7f, rate );

		float Distance( float t ) => MathF.Sqrt( miss * miss + speed * speed * t * t );
		var begins = first + Distance( first ) / SpeedOfSound;
		var ends = last + Distance( last ) / SpeedOfSound;
		const float lead = 0.001f;
		var heard = new float[(int)((ends - begins + 2f * lead) * rate)];
		var time = first;
		for ( var n = 0; n < heard.Length; n++ )
		{
			var arrives = begins - lead + n / rate;
			if ( arrives < begins || arrives > ends )
				continue;

			// When it was made: t + r(t) / c = arrives, which rises steadily with t below Mach 1.
			for ( var k = 0; k < 6; k++ )
			{
				var r = Distance( time );
				time -= (time + r / SpeedOfSound - arrives) / (1f + speed * speed * time / (r * SpeedOfSound));
			}

			time = Math.Clamp( time, first, last );
			var distance = Distance( time );
			var squeeze = 1f / (1f + speed * speed * time / (distance * SpeedOfSound));
			var at = (time - first) * rate;
			var i = Math.Min( (int)at, noise.Length - 2 );
			var sample = noise[i] + (noise[i + 1] - noise[i]) * (at - i);

			// Faded in and out over the first and last eighths of its flight.
			var along = (time - first) / (last - first);
			var fade = MathF.Min( 1f, MathF.Min( along, 1f - along ) * 8f );
			heard[n] = sample * miss / distance * squeeze * fade;
		}

		var clip = Store( $"hc1/flyby/whizz_{machIndex}_{missIndex}_{take}", Decimate( heard, factor ), lead + miss / SpeedOfSound - begins );
		if ( clip is null )
			return null;

		clip.Unit = 1f;
		Clips[key] = clip;
		return clip;
	}

	/// <summary> <paramref name="samples"/> as a mono 16-bit sound, normalised to <see cref="Headroom"/>. </summary>
	private static Clip Store( string name, float[] samples, float lead )
	{
		var peak = 0f;
		foreach ( var sample in samples )
			peak = MathF.Max( peak, MathF.Abs( sample ) );
		if ( peak <= 0f )
			return null;

		var scale = Headroom / peak * 32767f;
		var bytes = new byte[samples.Length * 2];
		for ( var i = 0; i < samples.Length; i++ )
		{
			var value = (short)Math.Clamp( (int)MathF.Round( samples[i] * scale ), -32768, 32767 );
			bytes[i * 2] = (byte)(value & 0xff);
			bytes[i * 2 + 1] = (byte)((value >> 8) & 0xff);
		}

		// Kept by name for the session, so a clip made before a hotload is found again.
		var file = SoundFile.FromPcm( name, bytes, new SoundFile.PcmOptions { Channels = 1, Rate = SampleRate, Bits = 16 } );
		return file.IsValid() ? new Clip { File = file, Unit = peak, Lead = lead } : null;
	}

	/// <summary> <paramref name="x"/> smoothed over <paramref name="width"/> samples (a Hann window): a shock's rise. </summary>
	private static float[] Smooth( float[] x, float width )
	{
		var taps = Math.Max( 1, (int)MathF.Round( width ) ) | 1;
		if ( taps == 1 )
			return x;

		var kernel = new float[taps];
		var sum = 0f;
		for ( var i = 0; i < taps; i++ )
			sum += kernel[i] = 0.5f - 0.5f * MathF.Cos( 2f * MathF.PI * (i + 1) / (taps + 1) );

		var half = taps / 2;
		var y = new float[x.Length];
		for ( var n = 0; n < x.Length; n++ )
		{
			var acc = 0f;
			for ( var i = 0; i < taps; i++ )
			{
				var j = n + i - half;
				if ( j >= 0 && j < x.Length )
					acc += kernel[i] * x[j];
			}

			y[n] = acc / sum;
		}

		return y;
	}

	/// <summary>
	/// <paramref name="x"/>, sampled at <see cref="SampleRate"/> x <paramref name="factor"/>, low-passed at 20 kHz
	/// (a Blackman-windowed sinc, no delay) and taken down to <see cref="SampleRate"/>.
	/// </summary>
	private static float[] Decimate( float[] x, int factor )
	{
		var taps = 64 * factor + 1;
		var half = taps / 2;
		var cutoff = 20000f / (SampleRate * factor);
		var kernel = new float[taps];
		var sum = 0f;
		for ( var i = 0; i < taps; i++ )
		{
			var n = i - half;
			var sinc = n == 0 ? 2f * cutoff : MathF.Sin( 2f * MathF.PI * cutoff * n ) / (MathF.PI * n);
			var phase = 2f * MathF.PI * i / (taps - 1);
			sum += kernel[i] = sinc * (0.42f - 0.5f * MathF.Cos( phase ) + 0.08f * MathF.Cos( 2f * phase ));
		}

		var y = new float[x.Length / factor];
		for ( var n = 0; n < y.Length; n++ )
		{
			var acc = 0f;
			for ( var i = 0; i < taps; i++ )
			{
				var j = n * factor + i - half;
				if ( j >= 0 && j < x.Length )
					acc += kernel[i] * x[j];
			}

			y[n] = acc / sum;
		}

		return y;
	}

	/// <summary> <paramref name="x"/> through a band-pass (RBJ's, 0 dB at its centre) at <paramref name="centre"/> Hz. </summary>
	private static float[] BandPass( float[] x, float centre, float q, float rate )
	{
		var w = 2f * MathF.PI * centre / rate;
		var alpha = MathF.Sin( w ) / (2f * q);
		var a0 = 1f + alpha;
		float b0 = alpha / a0, b2 = -alpha / a0, a1 = -2f * MathF.Cos( w ) / a0, a2 = (1f - alpha) / a0;
		var y = new float[x.Length];
		float x1 = 0f, x2 = 0f, y1 = 0f, y2 = 0f;
		for ( var n = 0; n < x.Length; n++ )
		{
			var output = b0 * x[n] + b2 * x2 - a1 * y1 - a2 * y2;
			x2 = x1;
			x1 = x[n];
			y2 = y1;
			y1 = output;
			y[n] = output;
		}

		return y;
	}
}
