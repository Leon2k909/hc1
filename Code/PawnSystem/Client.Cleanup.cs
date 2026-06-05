namespace Facepunch;

public partial class Client : Component.INetworkListener
{
	/// <summary>
	/// How long has it been since this player has d/c'd
	/// </summary>
	RealTimeSince TimeSinceDisconnected { get; set; }

	/// <summary>
	/// How long does it take to clean up a player once they disconnect?
	/// </summary>
	public static float DisconnectCleanupTime { get; set; } = 120f;

	void INetworkListener.OnDisconnected( Connection channel )
	{
		if ( Connection == channel )
		{
			TimeSinceDisconnected = 0;
		}
	}

	protected override void OnUpdate()
	{
		if ( IsLocalPlayer )
		{
			var currentTag = GameSettingsSystem.Current?.ClanTag;
			if ( ClanTag != currentTag )
			{
				UpdateClanTag( currentTag ?? "" );
			}
			var voice = Components.Get<PlayerVoiceComponent>();
			if ( voice.IsValid() )
			{
				var settings = GameSettingsSystem.Current;
				if ( !settings.VoiceEnabled )
				{
					voice.Mode = Sandbox.Voice.ActivateMode.Manual;
				}
				else
				{
					voice.Mode = settings.VoicePushToTalk ? Sandbox.Voice.ActivateMode.PushToTalk : Sandbox.Voice.ActivateMode.AlwaysOn;
					voice.PushToTalkInput = "voice";
				}
				voice.WorldspacePlayback = settings.VoiceProximity;
			}
		}

		if ( IsConnected ) return;
		if ( IsProxy ) return;

		if ( TimeSinceDisconnected > DisconnectCleanupTime )
		{
			GameObject.Destroy();
		}
	}
}
