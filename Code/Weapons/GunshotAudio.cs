namespace Facepunch;

/// <summary>
/// How a gunshot sounds away from the gun, for players' and bots' shots alike.
/// <para>
/// A muzzle blast spreads out as a sphere, so its level falls 6 dB every time the distance doubles (the inverse-distance
/// law), from where the recordings hold their level (<see cref="ReferenceDistance"/>, ~4 m) outwards: 14 dB down at 20 m,
/// 26 dB at 80 m, 38 dB at 330 m. The guns' own sound events fell only 9 dB by 79 m, so a fight anywhere on the map
/// sounded as if it was in the next room. The air also takes the top off a far shot (<see cref="SoundHandle.AirAbsorption"/>),
/// and a wall in between muffles it (<see cref="SoundHandle.OcclusionEnabled"/>), where the events had occlusion off.
/// </para>
/// <para>
/// The blast is louder in front of the muzzle than behind it: here 6 dB quieter straight behind the shot, 2.5 dB off to
/// the side (measured rifle blasts are 5-10 dB down behind).
/// </para>
/// <para>
/// Anyone else's shot is heard when its sound gets there, at the speed of sound (<see cref="PlayDelayed"/>): 0.3 s from
/// 100 m. Downrange of a supersonic round its crack comes first (<see cref="BulletFlyby"/>).
/// </para>
/// The shooter's own shot stays as it was: flat (2D) at full level.
/// </summary>
public static class GunshotAudio
{
	/// <summary> Where a shot's recording holds its level, ~4 m from the muzzle. Closer than this it stays at full level. </summary>
	public const float ReferenceDistance = 160f;

	/// <summary> Straight behind the muzzle, the blast's level against in front of it (-6 dB). </summary>
	private const float BehindGain = 0.5f;

	private static readonly Dictionary<float, Curve> Falloffs = new();

	/// <summary>
	/// Plays <paramref name="sound"/> for a shot fired at <paramref name="position"/> along <paramref name="forward"/>.
	/// <paramref name="own"/> is the viewer's own shot, which plays flat. <paramref name="volume"/> scales it (a part's
	/// sound volume, say). Null if nothing played.
	/// </summary>
	public static SoundHandle Play( SoundEvent sound, Vector3 position, Vector3 forward, bool own, float volume = 1f )
	{
		if ( sound is null )
			return null;

		if ( own )
		{
			if ( Sound.Play( sound, position ) is not { } flat )
				return null;

			flat.Volume *= volume;
			flat.SpacialBlend = 0f;
			return flat;
		}

		// Anyone else's shot reaches the listener at the speed of sound: 0.3 s from 100 m.
		if ( PlayDelayed( sound, position, SoundDelay( position ) ) is not { } handle )
			return null;

		handle.Volume *= volume;
		if ( sound.DistanceAttenuation && sound.Distance > ReferenceDistance )
		{
			handle.Distance = sound.Distance;
			handle.Falloff = FalloffFor( sound.Distance );
		}

		handle.OcclusionEnabled = true;
		handle.AirAbsorption = true;
		handle.Volume *= Directivity( position, forward );
		return handle;
	}

	/// <summary> How long a sound made at <paramref name="position"/> takes to reach the listener, in seconds. </summary>
	public static float SoundDelay( Vector3 position )
	{
		var listener = Game.ActiveScene?.Camera;
		return listener.IsValid() ? listener.WorldPosition.Distance( position ) / BulletFlyby.SoundSpeed : 0f;
	}

	/// <summary>
	/// Plays <paramref name="sound"/> at <paramref name="position"/> as <see cref="Sound.Play(SoundEvent, Vector3, float)"/>
	/// does (one of its files at random, its volume, pitch, mixer, distance, falloff, occlusion, air absorption and
	/// reverb), <paramref name="delay"/> seconds from now. Null if nothing played.
	/// <para>
	/// The engine delays a sound by holding back its samples, which it can only do once the file has loaded: a file
	/// played for the first time that hasn't loaded yet plays at once.
	/// </para>
	/// </summary>
	public static SoundHandle PlayDelayed( SoundEvent sound, Vector3 position, float delay )
	{
		if ( sound is null || Application.IsHeadless )
			return null;

		if ( delay <= 0.001f || sound.UI || sound.Sounds is not { Count: > 0 } files )
			return Sound.Play( sound, position );

		var file = files[Game.Random.Int( 0, files.Count - 1 )];
		if ( !file.IsValid() )
			return null;

		var handle = Sound.PlayFile( file, sound.Volume.GetValue(), pitch: sound.Pitch.GetValue(), delay: delay );
		if ( !handle.IsValid() )
			return null;

		handle.Position = position;
		handle.Distance = sound.Distance;
		handle.Falloff = sound.Falloff;
		handle.TargetMixer = sound.DefaultMixer.Get();
		handle.DistanceAttenuation = sound.DistanceAttenuation;
		handle.AirAbsorption = sound.AirAbsorption;
		handle.OcclusionEnabled = sound.OcclusionEnabled;
		handle.ReverbEnabled = sound.ReverbEnabled;
		return handle;
	}

	/// <summary> The blast's level towards the listener, from 1 in front of the muzzle to <see cref="BehindGain"/> behind it. </summary>
	private static float Directivity( Vector3 position, Vector3 forward )
	{
		var listener = Game.ActiveScene?.Camera;
		if ( !listener.IsValid() || forward.IsNearZeroLength )
			return 1f;

		var toListener = listener.WorldPosition - position;
		if ( toListener.LengthSquared < ReferenceDistance * ReferenceDistance )
			return 1f;

		var facing = Vector3.Dot( forward.Normal, toListener.Normal );
		return MathX.Lerp( BehindGain, 1f, (1f + facing) * 0.5f );
	}

	/// <summary>
	/// The inverse-distance law as a falloff over <paramref name="distance"/> (the curve runs 0-1 across it): full level
	/// out to <see cref="ReferenceDistance"/>, then ReferenceDistance / r, in linear steps half an octave apart (within
	/// 0.3 dB of the law), easing to silence over the last tenth.
	/// </summary>
	private static Curve FalloffFor( float distance )
	{
		if ( Falloffs.TryGetValue( distance, out var cached ) )
			return cached;

		var frames = new List<Curve.Frame> { Frame( 0f, 1f ) };
		for ( var r = ReferenceDistance; r < distance * 0.9f; r *= MathF.Sqrt( 2f ) )
			frames.Add( Frame( r / distance, ReferenceDistance / r ) );

		frames.Add( Frame( 0.9f, ReferenceDistance / (distance * 0.9f) ) );
		frames.Add( Frame( 1f, 0f ) );

		var curve = new Curve( frames );
		Falloffs[distance] = curve;
		return curve;
	}

	private static Curve.Frame Frame( float time, float value ) => new( time, value ) { Mode = Curve.HandleMode.Linear };
}
