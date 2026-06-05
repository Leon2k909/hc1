namespace Tec.AI;

/// <summary>
/// Singleton AudioAIManager. It is a singleton and not a static class because I want to clear the stims OnStart.
/// </summary>
public class AudioAIManager : Component
{
	private static AudioAIManager _instance;
	public static AudioAIManager Instance
	{
		get
		{
			if ( _instance == null )
			{
				// Auto-spawn the singleton if it doesn't exist
				_instance = new AudioAIManager();
				Log.Info( "AudioAIManager auto-spawned" );
			}
			return _instance;
		}
	}
	
	private AudioAIManager()
	{
		if ( _instance != null )
		{
			Log.Warning( "Attempted to create a second GameManager!" );
			return;
		}

		_instance = this;
		Log.Info( "GameManager initialized" );
	}
	
	public List<AudioStim> audioStims = new();

	public void Clear()
	{
		audioStims.Clear();
	}

	protected override void OnStart()
	{
		Clear();
	}

	public void NewAudioStim(AudioStim audioStim)
	{
		if(audioStim.DurationType != AudioStim.AudioStimDurationType.Instant)
		{
			audioStims.Add(audioStim);
		}
		else
		{
			// TODO Make NPCs check instant audio stims when they happened.
		}
	}

	public List<AudioStim> GetAudioStims()
	{
		List<AudioStim> validStims = [];
		
		//Reverse loop to avoid problems with removing elements.
		for ( int i = audioStims.Count - 1; i >= 0; i-- )
		{
			if ( audioStims[i].DurationType == AudioStim.AudioStimDurationType.Finite &&
			     audioStims[i].TimeSinceTriggered >= audioStims[i].Duration )
				audioStims.RemoveAt( i );
			else
				validStims.Add( audioStims[i] );
		}

		return validStims;
	}
}
