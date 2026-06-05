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

	protected override IEnumerable<Connection> ExcludeFilter()
	{
		if ( CommunicationMuteState.IsVoiceMuted( Client ) && Connection.Local is not null )
		{
			yield return Connection.Local;
		}

		var excludedConnections = Filter is null ? base.ExcludeFilter() : Filter.GetExcludeFilter();
		foreach ( var connection in excludedConnections )
		{
			if ( connection is not null )
				yield return connection;
		}
	}
}
