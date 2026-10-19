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
	/// Local shots retain their close, punchy sound, with a small spatial contribution so the room can respond.
/// </summary>
public static class GunshotAudio
{
	/// <summary> Where a shot's recording holds its level, ~4 m from the muzzle. Closer than this it stays at full level. </summary>
	public const float ReferenceDistance = 160f;

	/// <summary> Straight behind the muzzle, the blast's level against in front of it (-6 dB). </summary>
	private const float BehindGain = 0.5f;

	private static readonly Dictionary<float, Curve> Falloffs = new();
	private const float RoofReach = 1200f;
	private const float WallReach = 800f;
	private static readonly string[] AcousticTraceExclusions = { "trigger", "ragdoll", "player", "movement", "playerclip", "water" };
	private static readonly Vector3[] WallDirections = { Vector3.Forward, Vector3.Backward, Vector3.Left, Vector3.Right };

	/// <summary>
	/// How long (s) a muzzle's enclosure is kept, and how near (units) another shot has to be fired to take it, so a
	/// burst shares one set of probes. They reach 800-1200 units, so a step or two doesn't change what they find.
	/// </summary>
	private const float EnclosureLifetime = 0.4f;
	private const float EnclosureRadius = 48f;

	/// <summary>
	/// The quietest a room reflection is played, against the shot at <see cref="ReferenceDistance"/> (-40 dB). Further off
	/// it's lost under the shot's own reverb, and not worth two more voices with occlusion each: a shot in a closed room
	/// past ~77 m, or a third enclosed past ~25 m, plays without them.
	/// </summary>
	private const float QuietestReflection = 0.01f;

	/// <summary> A muzzle's enclosure, kept for the shots after it (<see cref="EnclosureAt"/>). </summary>
	private struct Enclosure
	{
		public bool Kept;
		public Vector3 Position;
		public float Value;
		public RealTimeSince Since;
	}

	private static readonly Enclosure[] Enclosures = new Enclosure[32];
	private static int _nextEnclosure;

	/// <summary>
	/// Plays <paramref name="sound"/> for a shot fired at <paramref name="position"/> along <paramref name="forward"/>.
	/// <paramref name="own"/> is the viewer's own shot, which plays flat. <paramref name="volume"/> scales it (a part's
	/// sound volume, say). Null if nothing played.
	/// </summary>
	public static SoundHandle Play( SoundEvent sound, Vector3 position, Vector3 forward, bool own, float volume = 1f )
	{
		if ( sound is null )
			return null;

		var room = EnclosureAt( position );

		if ( own )
		{
			if ( Sound.Play( sound, position ) is not { } flat )
				return null;

			flat.Volume *= volume;
			flat.SpacialBlend = 0.15f;
			flat.ReverbEnabled = true;
			flat.Reverb = MathX.Lerp( 0.15f, 1f, room );
			PlayRoomReflections( sound, position, volume, room, 0f, true );
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
		handle.ReverbEnabled = true;
		handle.Reverb = MathX.Lerp( 0.2f, 1f, room );
		var directionGain = Directivity( position, forward );
		handle.Volume *= directionGain;
		PlayRoomReflections( sound, position, volume * directionGain, room, SoundDelay( position ), false );
		return handle;
	}

	/// <summary>Amount of enclosure around a muzzle, from zero in the open to one in a closed room.</summary>
	public static float RoomEnclosure( Vector3 position )
	{
		var scene = Game.ActiveScene;
		if ( scene is null )
			return 0f;

		// Walls alone do not make a courtyard an indoor room.
		var roof = scene.Trace.Ray( position, position + Vector3.Up * RoofReach )
			.WithoutTags( AcousticTraceExclusions ).Run();
		if ( !roof.Hit || roof.GameObject?.Tags.Has( "sky" ) == true
			|| (roof.Surface?.ResourceName?.Contains( "sky", StringComparison.OrdinalIgnoreCase ) ?? false) )
			return 0f;

		var walls = 0;
		foreach ( var direction in WallDirections )
		{
			var hit = scene.Trace.Ray( position, position + direction * WallReach )
				.WithoutTags( AcousticTraceExclusions ).Run();
			if ( hit.Hit )
				walls++;
		}
		return Math.Clamp( (walls - 1f) / 3f, 0f, 1f );
	}

	/// <summary>
	/// <see cref="RoomEnclosure"/> at <paramref name="position"/>, or what it was for a shot fired within
	/// <see cref="EnclosureRadius"/> of it in the last <see cref="EnclosureLifetime"/>.
	/// </summary>
	private static float EnclosureAt( Vector3 position )
	{
		for ( var i = 0; i < Enclosures.Length; i++ )
		{
			ref var kept = ref Enclosures[i];
			if ( kept.Kept && kept.Since < EnclosureLifetime && (kept.Position - position).LengthSquared < EnclosureRadius * EnclosureRadius )
				return kept.Value;
		}

		var room = RoomEnclosure( position );
		Enclosures[_nextEnclosure] = new Enclosure { Kept = true, Position = position, Value = room, Since = 0f };
		_nextEnclosure = (_nextEnclosure + 1) % Enclosures.Length;
		return room;
	}

	/// <summary>Early room reflections, audible even with a very quiet native reverb mix.</summary>
	private static void PlayRoomReflections( SoundEvent sound, Vector3 position, float volume, float room, float delay, bool own )
	{
		if ( room <= 0f || sound.UI || Application.IsHeadless )
			return;

		// Anyone else's shot falls off with the inverse-distance law (FalloffFor), and its reflections with it.
		if ( !own && sound.DistanceAttenuation && sound.Distance > ReferenceDistance
			&& Game.ActiveScene?.Camera is { } listener && listener.IsValid() )
		{
			var distance = listener.WorldPosition.Distance( position );
			if ( distance >= sound.Distance
				|| volume * room * 0.19f * ReferenceDistance / MathF.Max( distance, ReferenceDistance ) < QuietestReflection )
				return;
		}

		for ( var i = 0; i < 2; i++ )
		{
			var reflection = PlayDelayed( sound, position, delay + (i == 0 ? 0.065f : 0.145f) );
			if ( reflection is null )
				continue;

			reflection.Volume *= volume * room * (i == 0 ? 0.19f : 0.10f);
			reflection.SpacialBlend = own ? 0.35f : 1f;
			reflection.DistanceAttenuation = !own && sound.DistanceAttenuation;
			if ( reflection.DistanceAttenuation && sound.Distance > ReferenceDistance )
			{
				reflection.Distance = sound.Distance;
				reflection.Falloff = FalloffFor( sound.Distance );
			}
			reflection.OcclusionEnabled = !own;
			reflection.AirAbsorption = !own;
			reflection.ReverbEnabled = true;
			reflection.Reverb = 1f;
		}
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
