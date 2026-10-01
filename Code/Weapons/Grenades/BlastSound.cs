namespace Facepunch;

/// <summary>
/// An explosion's sound, as each machine's listener hears it: the near set (the bang, the fragments and the debris
/// coming down) or, beyond <see cref="FarDistance"/>, the far set (the bang dulled by the air, the echoes and the
/// rumble round the listener). Either arrives when the sound gets there, at the speed of sound
/// (<see cref="GunshotAudio.PlayDelayed"/>): 0.3 s from 100 m. Tools/ordnance_sounds.py makes both sets.
/// </summary>
[Title( "Blast Sound" )]
public sealed class BlastSound : Component
{
	[Property] public SoundEvent Near { get; set; }
	[Property] public SoundEvent Far { get; set; }

	/// <summary>
	/// Further than this from the listener, the far set plays. ordnance_sounds.py's <c>FAR_DISTANCES</c> holds the same
	/// figure, where the near set's falloff has brought it to the far set's level.
	/// </summary>
	[Property] public float FarDistance { get; set; } = 1600f;

	protected override void OnStart()
	{
		var listener = Scene.Camera;
		var distance = listener.IsValid() ? listener.WorldPosition.Distance( WorldPosition ) : 0f;
		var sound = distance > FarDistance && Far is not null ? Far : Near;
		GunshotAudio.PlayDelayed( sound, WorldPosition, GunshotAudio.SoundDelay( WorldPosition ) );
	}
}
