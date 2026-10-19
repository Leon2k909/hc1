using Sandbox.Audio;

namespace Facepunch;

/// <summary>
/// Temporary deafness after a bang close by (a flashbang's: <see cref="FlashbangEffect"/>): the ears' threshold shift.
/// Everything the character hears goes quiet and dull, the highs first, then comes back as the ears recover, with the
/// ringing (which isn't muffled) over it. At full <see cref="Level"/> the world is <see cref="MaxAttenuationDb"/> quieter
/// and nothing above ~<see cref="DeafCutoff"/> Hz gets through: about what's left a moment after a stun grenade goes
/// off a couple of metres away.
/// <para>
/// It's applied to the Game mixer, which every world sound plays through (<see cref="DeafnessProcessor"/>), as the
/// <see cref="AcousticReflex"/> is. The music, UI, radio and voice chat mixers aren't the character's ears, so they're
/// left alone.
/// </para>
/// </summary>
public static class Deafness
{
	/// <summary> How much quieter the world is at full deafness, in dB. </summary>
	public const float MaxAttenuationDb = 36f;

	/// <summary> The highest frequency that still gets through at full deafness, in Hz. </summary>
	public const float DeafCutoff = 250f;

	/// <summary> How deaf the ears are, 0 (hearing) to 1 (next to nothing). Set every frame while it lasts. </summary>
	public static float Level { get; private set; }

	private static DeafnessProcessor _processor;

	public static void Set( float level )
	{
		Level = Math.Clamp( level, 0f, 1f );
		if ( Level > 0f && !Application.IsHeadless )
			EnsureProcessor();
	}

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
			if ( processor.GetType().Name == nameof( DeafnessProcessor ) )
				mixer.RemoveProcessor( processor );
		}

		_processor = new DeafnessProcessor { Mix = 1f };
		mixer.AddProcessor( _processor );
	}
}

/// <summary>
/// <see cref="Deafness"/>'s filter: a gain and a two-pole low-pass whose cutoff falls from 20 kHz to
/// <see cref="Deafness.DeafCutoff"/> on a log scale with the level. Both ease over ~10 ms so the level can change every
/// frame with no clicks, and at rest the sound goes through untouched.
/// </summary>
public sealed class DeafnessProcessor : AudioProcessor<DeafnessProcessor.State>
{
	/// <summary> s&amp;box mixes at 44.1 kHz. </summary>
	private const float SampleRate = 44100f;

	private const float OpenCutoff = 20000f;

	private static readonly float Ease = 1f - MathF.Exp( -1f / (0.01f * SampleRate) );

	public sealed class State : AudioProcessor.ListenerState
	{
		public PerChannel<float> First;
		public PerChannel<float> Second;

		/// <summary> How far the filter is in, 0 (bypassed) to 1. </summary>
		public PerChannel<float> Wet;
		public PerChannel<float> Gain;
		public PerChannel<float> Alpha;
	}

	private static float AlphaFor( float cutoff ) => 1f - MathF.Exp( -2f * MathF.PI * cutoff / SampleRate );

	protected override void ProcessSingleChannel( AudioChannel channel, Span<float> input )
	{
		var state = CurrentState;
		if ( state is null || input.Length == 0 )
			return;

		var level = Deafness.Level;
		var wet = state.Wet.Get( channel );
		if ( level <= 0f && wet <= 0f )
		{
			// At rest: the sound goes through as it is, and the filter follows it, ready to come in without a click.
			var last = input[^1];
			state.First.Set( channel, last );
			state.Second.Set( channel, last );
			state.Gain.Set( channel, 1f );
			state.Alpha.Set( channel, AlphaFor( OpenCutoff ) );
			return;
		}

		var targetWet = level > 0f ? 1f : 0f;
		var targetGain = MathF.Pow( 10f, -Deafness.MaxAttenuationDb * level / 20f );
		var targetAlpha = AlphaFor( OpenCutoff * MathF.Pow( Deafness.DeafCutoff / OpenCutoff, level ) );

		var first = state.First.Get( channel );
		var second = state.Second.Get( channel );
		var gain = state.Gain.Get( channel );
		var alpha = state.Alpha.Get( channel );
		if ( alpha <= 0f ) alpha = AlphaFor( OpenCutoff );
		for ( var i = 0; i < input.Length; i++ )
		{
			wet += (targetWet - wet) * Ease;
			gain += (targetGain - gain) * Ease;
			alpha += (targetAlpha - alpha) * Ease;
			var x = input[i];
			first += alpha * (x - first);
			second += alpha * (first - second);
			input[i] = x + (second * gain - x) * wet;
		}

		// No denormals while it idles in silence.
		state.First.Set( channel, MathF.Abs( first ) < 1e-20f ? 0f : first );
		state.Second.Set( channel, MathF.Abs( second ) < 1e-20f ? 0f : second );
		state.Gain.Set( channel, gain );
		state.Alpha.Set( channel, alpha );
		state.Wet.Set( channel, wet < 1e-4f && targetWet == 0f ? 0f : wet );
	}
}
