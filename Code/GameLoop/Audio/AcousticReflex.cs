using Sandbox.Audio;

namespace Facepunch;

/// <summary>
/// The ear's acoustic reflex: after a loud enough sound the stapedius muscle tightens the chain of bones in the middle
/// ear, which takes 10-20 dB off what comes after below ~1 kHz and little above 2 kHz. It starts too late to soften
/// the sound that set it off: 25-35 ms after a strong one, over 100 ms near its threshold. So a bullet's crack goes in
/// whole, and the report that follows it is duller and quieter, the more so the closer the round came. After one short
/// sound the muscle relaxes again within a few hundred milliseconds.
/// <para>
/// What sets it off is the sound's energy over the ear's ~200 ms integration, not its peak: a crack of 1 m off the path
/// (~985 Pa for 106 us) is ~116 dB over those 200 ms, well past the ~85 dB threshold, one 20 m off ~100 dB, one 100 m
/// off ~91 dB (<see cref="Impulse"/>). The strength grows over <see cref="FullRangeDb"/> above the threshold.
/// </para>
/// <para>
/// It's applied to the Game mixer, which every world sound plays through (<see cref="ReflexProcessor"/>): a low shelf
/// that cuts up to <see cref="MaxAttenuationDb"/> under ~500 Hz, ~9 dB at 1 kHz, ~5 dB at 2 kHz and under 2 dB above
/// 4 kHz at full strength. The music, UI, radio and voice chat mixers aren't the character's ears, so they're left
/// alone. The timings and threshold are textbook figures, not measured on these sounds: tune them by ear.
/// </para>
/// </summary>
public static class AcousticReflex
{
	/// <summary> The reflex threshold, as an impulse's energy spread over <see cref="IntegrationTime"/>, in dB SPL. </summary>
	private const float ThresholdDb = 85f;

	/// <summary> How far over the threshold the reflex is at full strength, in dB. </summary>
	private const float FullRangeDb = 25f;

	/// <summary> The cut below ~500 Hz at full strength, in dB. </summary>
	public const float MaxAttenuationDb = 15f;

	/// <summary> The ear's integration time for the reflex, in seconds. </summary>
	private const float IntegrationTime = 0.2f;

	/// <summary> The reflex's latency near its threshold and at full strength, in seconds. </summary>
	private const float SlowLatency = 0.12f;
	private const float FastLatency = 0.03f;

	/// <summary>
	/// The contraction's rise and relaxation time constants, in seconds: it peaks ~60 ms after it starts and has let go
	/// to a twentieth ~0.5 s later.
	/// </summary>
	private const float Rise = 0.03f;
	private const float Relax = 0.15f;

	/// <summary> The peak of <c>exp(-t / Relax) - exp(-t / Rise)</c>, which a twitch is divided by. </summary>
	private static readonly float TwitchPeak = TwitchShape( MathF.Log( Relax / Rise ) * Rise * Relax / (Relax - Rise) );

	/// <summary> Sounds arriving closer together than this (s) set off one twitch between them, their energies added. </summary>
	private const float MergeWindow = 0.05f;

	private readonly struct Twitch
	{
		/// <summary> When the sound that set it off arrived, and its energy (Pa^2 s). </summary>
		public readonly double Arrival;
		public readonly float Energy;

		public readonly double Onset;
		public readonly float Strength;

		public Twitch( double arrival, float energy )
		{
			Arrival = arrival;
			Energy = energy;
			var level = 10f * MathF.Log10( energy / IntegrationTime / (20e-6f * 20e-6f) );
			Strength = Math.Clamp( (level - ThresholdDb) / FullRangeDb, 0f, 1f );
			Onset = arrival + (SlowLatency + (FastLatency - SlowLatency) * Strength);
		}
	}

	/// <summary> The twitches still under way. Replaced whole, never changed, since the mixing thread reads it. </summary>
	private static Twitch[] _twitches = Array.Empty<Twitch>();

	private static ReflexProcessor _processor;

	/// <summary>
	/// A short sound reaching the ear <paramref name="delay"/> seconds from now, of peak pressure
	/// <paramref name="peakPascals"/> lasting <paramref name="duration"/> seconds, whose mean square over that time is
	/// <paramref name="meanSquareShare"/> of the peak's square (a third for an N-wave). Ones too quiet on their own are
	/// kept too, since a shotgun's pellets crack almost together.
	/// </summary>
	public static void Impulse( float peakPascals, float duration, float meanSquareShare, float delay )
	{
		if ( Application.IsHeadless || peakPascals <= 0f || duration <= 0f )
			return;

		var now = RealTime.NowDouble;
		var twitch = new Twitch( now + delay, peakPascals * peakPascals * meanSquareShare * duration );
		var kept = new List<Twitch>( _twitches.Length + 1 );
		foreach ( var other in _twitches )
		{
			// Gone to under a thousandth of its peak.
			if ( now - other.Onset >= Relax * 7f )
				continue;

			if ( Math.Abs( other.Arrival - twitch.Arrival ) < MergeWindow )
				twitch = new Twitch( Math.Min( other.Arrival, twitch.Arrival ), other.Energy + twitch.Energy );
			else
				kept.Add( other );
		}

		kept.Add( twitch );
		_twitches = kept.ToArray();
		if ( twitch.Strength > 0f )
			EnsureProcessor();
	}

	/// <summary> How far the muscle is contracted at <paramref name="now"/> (<see cref="RealTime.NowDouble"/>), 0 to 1. </summary>
	internal static float Contraction( double now )
	{
		var twitches = _twitches;
		if ( twitches.Length == 0 )
			return 0f;

		// Twitches close together add up, but never past full. One gone to under a thousandth of its peak is over.
		var slack = 1f;
		foreach ( var twitch in twitches )
		{
			var since = (float)(now - twitch.Onset);
			if ( since > 0f && since < Relax * 7f )
				slack *= 1f - twitch.Strength * Math.Clamp( TwitchShape( since ) / TwitchPeak, 0f, 1f );
		}

		return 1f - slack;
	}

	private static float TwitchShape( float since ) => MathF.Exp( -since / Relax ) - MathF.Exp( -since / Rise );

	/// <summary>
	/// Puts the processor on the Game mixer once. A hotload can leave the old code's processor there, so any by the same
	/// name is taken off first.
	/// </summary>
	private static void EnsureProcessor()
	{
		var mixer = Mixer.FindMixerByName( "Game" ) ?? Mixer.Default;
		if ( mixer is null )
			return;

		var processors = mixer.GetProcessors();
		if ( _processor is not null && processors.Contains( _processor ) )
			return;

		foreach ( var processor in processors )
		{
			if ( processor.GetType().Name == nameof( ReflexProcessor ) )
				mixer.RemoveProcessor( processor );
		}

		_processor = new ReflexProcessor { Mix = 1f };
		mixer.AddProcessor( _processor );
	}
}

/// <summary>
/// The acoustic reflex's filter (<see cref="AcousticReflex"/>): two first-order low shelves at 2 kHz in a row, each
/// <c>x - cut * lowpass(x)</c>, so the cut can change every sample with no clicks. It eases to the contraction over
/// 5 ms, and at rest it passes the sound through unchanged.
/// </summary>
public sealed class ReflexProcessor : AudioProcessor<ReflexProcessor.State>
{
	/// <summary> s&amp;box mixes at 44.1 kHz. </summary>
	private const float SampleRate = 44100f;

	private const float Corner = 2000f;

	private static readonly float Alpha = 1f - MathF.Exp( -2f * MathF.PI * Corner / SampleRate );
	private static readonly float Ease = 1f - MathF.Exp( -1f / (0.005f * SampleRate) );

	public sealed class State : AudioProcessor.ListenerState
	{
		public PerChannel<float> First;
		public PerChannel<float> Second;

		/// <summary> Each stage's cut, 1 less its gain below the corner. </summary>
		public PerChannel<float> Cut;
	}

	protected override void ProcessSingleChannel( AudioChannel channel, Span<float> input )
	{
		var state = CurrentState;
		if ( state is null )
			return;

		// Each stage takes half the dB.
		var contraction = AcousticReflex.Contraction( RealTime.NowDouble );
		var target = 1f - MathF.Pow( 10f, -AcousticReflex.MaxAttenuationDb * contraction / 40f );

		var cut = state.Cut.Get( channel );
		if ( target <= 0f && cut <= 0f )
		{
			// At rest: the sound goes through as it is. The low-passes start again from silence, and settle within
			// a few samples, long before the cut has eased in.
			state.First.Set( channel, 0f );
			state.Second.Set( channel, 0f );
			return;
		}

		var first = state.First.Get( channel );
		var second = state.Second.Get( channel );
		for ( var i = 0; i < input.Length; i++ )
		{
			cut += (target - cut) * Ease;
			var x = input[i];
			first += Alpha * (x - first);
			var y = x - cut * first;
			second += Alpha * (y - second);
			input[i] = y - cut * second;
		}

		// No denormals while it idles in silence.
		state.First.Set( channel, MathF.Abs( first ) < 1e-20f ? 0f : first );
		state.Second.Set( channel, MathF.Abs( second ) < 1e-20f ? 0f : second );
		state.Cut.Set( channel, cut < 1e-6f && target == 0f ? 0f : cut );
	}
}
