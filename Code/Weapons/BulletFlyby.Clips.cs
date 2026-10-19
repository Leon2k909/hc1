using Sandbox.Diagnostics;
using System.Threading.Tasks;

namespace Facepunch;

/// <summary>
/// <see cref="BulletFlyby"/>'s sounds: each crack, whizz and tail is drawn here from its own seed, so it comes out the
/// same wherever and whenever it's made.
/// <para>
/// They're all made ahead, once a session (<see cref="Prepare"/>): the samples on a worker thread, then a few a frame
/// made into sounds, which only the main thread can do. Made as they were first needed, each took a few milliseconds
/// (a whizz runs ~50k samples through a 257-tap filter), and with ~300 of them the first minutes of a match hitched. One
/// needed before it's ready is still made there and then.
/// </para>
/// </summary>
public static partial class BulletFlyby
{
	private const int SampleRate = 44100;

	/// <summary> Clips are normalised to this peak. </summary>
	private const float Headroom = 0.9f;

	/// <summary> The shortest crack clip (s); each next one is <see cref="CrackStep"/> times longer. </summary>
	private const float ShortestCrack = 40e-6f;
	private const float CrackStep = 1.2f;
	private const int CrackSteps = 21;

	/// <summary>
	/// The grains' decay times (s), and the cracks they're made of (<see cref="MakeCrack"/>'s index: ~80, 170, 300 and
	/// 620 us long).
	/// </summary>
	private static readonly float[] TailDecays = { 0.003f, 0.008f, 0.02f, 0.05f, 0.12f };
	private static readonly int[] TailCracks = { 4, 8, 11, 15 };

	/// <summary> The whizz clips' bullet speeds (Mach) and misses (m). </summary>
	private static readonly float[] WhizzMachs = { 0.75f, 0.9f };
	private static readonly float[] WhizzMisses = { 0.5f, 1f, 2f, 4f };

	/// <summary> Main-thread time a frame may spend making clips made ahead into sounds, in milliseconds. </summary>
	private const double RealiseBudget = 0.5;

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
		/// <summary> The name the engine keeps its sound by for the session. </summary>
		public string Name;

		/// <summary> The sound, once the main thread has made it (<see cref="Realise"/>). </summary>
		public SoundFile File;

		/// <summary> A crack's band-limited peak for a unit N-wave. A whizz's is 1: its level is its peak. </summary>
		public float Unit;

		/// <summary> Seconds into the clip that a crack's front, or a whizz's closest pass, arrives. </summary>
		public float Lead;

		/// <summary>
		/// The samples before they were normalised, their peak (which they're normalised by) and their energy (the sum of
		/// their squares over the rate).
		/// </summary>
		public float[] Samples;
		public float Peak;
		public float Energy;
	}

	private static readonly Dictionary<int, Clip> Clips = new();
	private static readonly Dictionary<int, Clip> Tails = new();

	/// <summary> Clips made ahead, waiting for the main thread to make them sounds. </summary>
	private static readonly Queue<Clip> Unrealised = new();

	private static bool _madeAhead;

	/// <summary>
	/// Once a session, starts making every clip on a worker thread; after that, makes those it's made into sounds, for
	/// up to <see cref="RealiseBudget"/> a frame. Called every frame (<see cref="BulletFlybyClips"/>).
	/// </summary>
	public static void Prepare()
	{
		if ( Application.IsHeadless )
			return;

		if ( !_madeAhead )
		{
			_madeAhead = true;
			_ = MakeAhead();
			return;
		}

		if ( Unrealised.Count == 0 )
			return;

		var timer = FastTimer.StartNew();
		while ( Unrealised.Count > 0 && timer.ElapsedMilliSeconds < RealiseBudget )
			Realise( Unrealised.Dequeue() );
	}

	private static async Task MakeAhead()
	{
		try
		{
			var (clips, tails) = await GameTask.RunInThreadAsync( MakeAll );
			Keep( Clips, clips );
			Keep( Tails, tails );
		}
		catch ( Exception e )
		{
			Log.Warning( $"BulletFlyby: couldn't make the clips ahead, so they're made as they're needed ({e.Message})" );
		}
	}

	/// <summary> Takes the clips made ahead into <paramref name="into"/>, but for any made there meanwhile, which are the same. </summary>
	private static void Keep( Dictionary<int, Clip> into, Dictionary<int, Clip> made )
	{
		foreach ( var (key, clip) in made )
		{
			if ( Usable( into, key, out _ ) )
				continue;

			into[key] = clip;
			Unrealised.Enqueue( clip );
		}
	}

	/// <summary>
	/// Every clip a crack, whizz or tail can ask for, keyed as they're looked up. On a worker thread: it touches nothing
	/// shared, and each clip is drawn from its own seed.
	/// </summary>
	private static (Dictionary<int, Clip> Clips, Dictionary<int, Clip> Tails) MakeAll()
	{
		var clips = new Dictionary<int, Clip>();
		for ( var index = 0; index < CrackSteps; index++ )
		{
			for ( var front = Front.Sharp; front <= Front.Soft; front++ )
			{
				for ( var take = 0; take < 2; take++ )
				{
					if ( CrackClip( index, front, take ) is { } crack )
						clips[CrackKey( index, front, take )] = crack;
				}
			}
		}

		for ( var mach = 0; mach < WhizzMachs.Length; mach++ )
		{
			for ( var miss = 0; miss < WhizzMisses.Length; miss++ )
			{
				for ( var take = 0; take < 2; take++ )
				{
					if ( WhizzClip( mach, miss, take ) is { } whizz )
						clips[WhizzKey( mach, miss, take )] = whizz;
				}
			}
		}

		var tails = new Dictionary<int, Clip>();
		for ( var decay = 0; decay < TailDecays.Length; decay++ )
		{
			for ( var crack = 0; crack < TailCracks.Length; crack++ )
			{
				for ( var soft = 0; soft < 2; soft++ )
				{
					for ( var take = 0; take < 2; take++ )
					{
						var front = soft == 1 ? Front.Soft : Front.Rounded;
						if ( clips.TryGetValue( CrackKey( TailCracks[crack], front, take ), out var cracks )
							&& ScatterClip( decay, crack, soft == 1, take, cracks ) is { } tail )
							tails[TailKey( decay, crack, soft == 1, take )] = tail;
					}
				}
			}
		}

		return (clips, tails);
	}

	/// <summary> A clip already made under <paramref name="key"/>, if there's one (a hotload can leave one half there). </summary>
	private static bool Usable( Dictionary<int, Clip> clips, int key, out Clip clip ) =>
		clips.TryGetValue( key, out clip ) && clip?.Samples is not null && clip.Name is not null;

	private static int CrackKey( int index, Front front, int take ) => ((index * 8 + (int)front) * 2 + take) * 2;
	private static int WhizzKey( int machIndex, int missIndex, int take ) => ((machIndex * 4 + missIndex) * 2 + take) * 2 + 1;
	private static int TailKey( int decayIndex, int crackIndex, bool soft, int take ) =>
		((decayIndex * TailCracks.Length + crackIndex) * 2 + (soft ? 1 : 0)) * 2 + take;

	/// <summary> The crack clip <see cref="CrackClip"/> draws, made a sound. </summary>
	private static Clip MakeCrack( int index, Front front, int take )
	{
		var key = CrackKey( index, front, take );
		if ( !Usable( Clips, key, out var clip ) )
		{
			clip = CrackClip( index, front, take );
			if ( clip is null )
				return null;

			Clips[key] = clip;
		}

		return Realise( clip ) ? clip : null;
	}

	/// <summary> The tail grain <see cref="ScatterClip"/> draws, made a sound. </summary>
	private static Clip MakeScatter( int decayIndex, int crackIndex, bool soft, int take )
	{
		var key = TailKey( decayIndex, crackIndex, soft, take );
		if ( !Usable( Tails, key, out var clip ) )
		{
			var crack = MakeCrack( TailCracks[crackIndex], soft ? Front.Soft : Front.Rounded, take );
			if ( crack is null )
				return null;

			clip = ScatterClip( decayIndex, crackIndex, soft, take, crack );
			if ( clip is null )
				return null;

			Tails[key] = clip;
		}

		return Realise( clip ) ? clip : null;
	}

	/// <summary> The whizz clip <see cref="WhizzClip"/> draws, made a sound. </summary>
	private static Clip MakeWhizz( int machIndex, int missIndex, int take )
	{
		var key = WhizzKey( machIndex, missIndex, take );
		if ( !Usable( Clips, key, out var clip ) )
		{
			clip = WhizzClip( machIndex, missIndex, take );
			if ( clip is null )
				return null;

			Clips[key] = clip;
		}

		return Realise( clip ) ? clip : null;
	}

	/// <summary>
	/// A crack clip: an N-wave <see cref="ShortestCrack"/> x <see cref="CrackStep"/>^<paramref name="index"/> long, with
	/// its shocks shaped as <paramref name="front"/>, drawn at 16 times the output's rate, band-limited to 20 kHz and
	/// normalised. <paramref name="take"/> picks one of two draws, whose shocks fall at other points between samples.
	/// </summary>
	private static Clip CrackClip( int index, Front front, int take )
	{
		const int factor = 16;
		var rate = (float)SampleRate * factor;
		var random = new Random( CrackKey( index, front, take ) * 7919 + 17 );
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
		return Measure( $"hc1/flyby/crack_{index:00}_{front.ToString().ToLowerInvariant()}_{take}", Decimate( wave, factor ), lead );
	}

	/// <summary>
	/// A tail grain: cracks of <see cref="TailCracks"/>[<paramref name="crackIndex"/>]'s length, rounded as scattering
	/// leaves them (or soft, off grass and earth), coming in from patch after patch, ~6000 a second at random (a Poisson
	/// train) with random strength and sign, fading as <c>exp(-t / tau)</c> for tau of
	/// <see cref="TailDecays"/>[<paramref name="decayIndex"/>] after a 0.5 ms rise. <paramref name="crack"/> is that crack.
	/// </summary>
	private static Clip ScatterClip( int decayIndex, int crackIndex, bool soft, int take, Clip crack )
	{
		if ( crack?.Samples is null )
			return null;

		const float density = 6000f;
		const float rise = 0.0005f;
		var decay = TailDecays[decayIndex];
		var span = 5f * decay;
		var random = new Random( TailKey( decayIndex, crackIndex, soft, take ) * 7919 + 43 );
		var tail = new float[(int)(span * SampleRate) + crack.Samples.Length + 1];
		var time = 0f;
		while ( true )
		{
			time += -MathF.Log( 1f - (float)random.NextDouble() ) / density;
			if ( time > span )
				break;

			var gaussian = MathF.Sqrt( -2f * MathF.Log( 1f - (float)random.NextDouble() ) ) * MathF.Cos( 2f * MathF.PI * (float)random.NextDouble() );
			var weight = gaussian * MathF.Exp( -time / decay ) * MathF.Min( 1f, time / rise );
			var at = (int)(time * SampleRate);
			for ( var i = 0; i < crack.Samples.Length; i++ )
				tail[at + i] += weight * crack.Samples[i];
		}

		return Measure( $"hc1/flyby/tail_{decayIndex}_{crackIndex}_{(soft ? "soft" : "hard")}_{take}", tail, crack.Lead );
	}

	/// <summary>
	/// A whizz clip: a round at <see cref="WhizzMachs"/>[<paramref name="machIndex"/>] passing
	/// <see cref="WhizzMisses"/>[<paramref name="missIndex"/>] away. Its wake's rush (noise a couple of octaves wide round
	/// its shedding frequency, 0.2 v / d for a 10 mm bullet) is heard as it arrives: each moment of it at the time it
	/// was made plus its way to the listener, so the approach comes squeezed up in pitch and the going stretched down,
	/// louder coming than going.
	/// </summary>
	private static Clip WhizzClip( int machIndex, int missIndex, int take )
	{
		const int factor = 4;
		var rate = (float)SampleRate * factor;
		var random = new Random( WhizzKey( machIndex, missIndex, take ) * 7919 + 29 );
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

		var clip = Measure( $"hc1/flyby/whizz_{machIndex}_{missIndex}_{take}", Decimate( heard, factor ), lead + miss / SpeedOfSound - begins );
		if ( clip is not null )
			clip.Unit = 1f;
		return clip;
	}

	/// <summary> <paramref name="samples"/> as a clip, with their peak and energy, to be made a sound. Null if they're silent. </summary>
	private static Clip Measure( string name, float[] samples, float lead )
	{
		var peak = 0f;
		var energy = 0f;
		foreach ( var sample in samples )
		{
			peak = MathF.Max( peak, MathF.Abs( sample ) );
			energy += sample * sample;
		}

		if ( peak <= 0f )
			return null;

		return new Clip { Name = name, Unit = peak, Lead = lead, Samples = samples, Peak = peak, Energy = energy / SampleRate };
	}

	/// <summary>
	/// Makes <paramref name="clip"/> a mono 16-bit sound, normalised to <see cref="Headroom"/>, if it isn't one yet. Only
	/// the main thread can. False if it couldn't be made.
	/// </summary>
	private static bool Realise( Clip clip )
	{
		if ( clip is null )
			return false;

		if ( clip.File.IsValid() )
			return true;

		var samples = clip.Samples;
		var scale = Headroom / clip.Peak * 32767f;
		var bytes = new byte[samples.Length * 2];
		for ( var i = 0; i < samples.Length; i++ )
		{
			var value = (short)Math.Clamp( (int)MathF.Round( samples[i] * scale ), -32768, 32767 );
			bytes[i * 2] = (byte)(value & 0xff);
			bytes[i * 2 + 1] = (byte)((value >> 8) & 0xff);
		}

		// Kept by name for the session, so a clip made before a hotload is found again.
		clip.File = SoundFile.FromPcm( clip.Name, bytes, new SoundFile.PcmOptions { Channels = 1, Rate = SampleRate, Bits = 16 } );
		return clip.File.IsValid();
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

/// <summary> Has <see cref="BulletFlyby"/>'s clips made before anyone needs them (<see cref="BulletFlyby.Prepare"/>). </summary>
public sealed class BulletFlybyClips : GameObjectSystem<BulletFlybyClips>
{
	public BulletFlybyClips( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, 0, Prepare, "BulletFlybyClips" );
	}

	private void Prepare()
	{
		if ( Scene.IsEditor )
			return;

		BulletFlyby.Prepare();
	}
}
