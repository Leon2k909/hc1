using Sandbox;
using Sandbox.Audio;

namespace Facepunch;

/// <summary>
/// An implementation of <see cref="Voice"/>, which takes use of an active Component which implements <see cref="IVoiceFilter"/>.
/// </summary>
public partial class PlayerVoiceComponent : Voice
{
	/// <summary>
	/// The target <see cref="Client"/>
	/// </summary>
	[Property] public Client Client { get; set; }

	/// <summary>
	/// The cached <see cref="IVoiceFilter"/> which is grabbed on <see cref="OnStart"/>.
	/// </summary>
	IVoiceFilter Filter { get; set; }

	protected override void OnStart()
	{
		Filter = Scene.GetAllComponents<IVoiceFilter>().FirstOrDefault();
		TargetMixer = Mixer.FindMixerByName( "Voice" );
	}

	/// <summary>
	/// Who doesn't get our voice. This runs on the speaker's machine, so the listener's mutes can't go here.
	/// </summary>
	protected override IEnumerable<Connection> ExcludeFilter()
	{
		var excludedConnections = Filter is null ? base.ExcludeFilter() : Filter.GetExcludeFilter();
		foreach ( var connection in excludedConnections )
		{
			if ( connection is not null )
				yield return connection;
		}
	}

	/// <summary>
	/// A player we've muted (the scoreboard's mic button) isn't played. This runs on the listener's machine, where the
	/// mute is: it used to be checked in <see cref="ExcludeFilter"/>, on the speaker's, so muting did nothing.
	/// </summary>
	protected override bool ShouldHearVoice( Connection connection )
	{
		var speaker = Client.IsValid() ? Client : GetComponent<Client>();
		return !CommunicationMuteState.IsVoiceMuted( speaker ) && base.ShouldHearVoice( connection );
	}
}
