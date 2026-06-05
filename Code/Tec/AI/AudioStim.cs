namespace Tec.AI;

public class AudioStim
{
	public enum AudioStimType
	{
		Undefined,
		Shoot,
		Footstep
	}

	public enum AudioStimDurationType
	{
		Instant,
		Finite,
		Continuous  // needs manual removal
	}

	public AudioStim(Faction faction, Vector3 position, float range, AudioStimType audioStimType = AudioStimType.Undefined, AudioStimDurationType durationType = AudioStimDurationType.Finite, float duration = 0.6f)
	{
		Faction = faction;
		Position = position;
		Range = range;
		StimType = audioStimType;
		DurationType = durationType;
		Duration = duration;
		TimeSinceTriggered = 0f;
		AudioAIManager.Instance.NewAudioStim(this);
	}

	public Faction Faction { get; }
	public Vector3 Position { get; }
	public float Range { get; }
	public AudioStimType StimType { get; }
	public AudioStimDurationType DurationType { get; }
	public float Duration { get; }
	public TimeSince TimeSinceTriggered { get; private set; }
	// public Globals.Faction faction;
}
