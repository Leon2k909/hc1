namespace Facepunch;

public partial class Client : Component.INetworkListener
{
	/// <summary>
	/// How long has it been since this player has d/c'd
	/// </summary>
	RealTimeSince TimeSinceDisconnected { get; set; }

	/// <summary> Sent again a second later while the host hasn't got them, rather than every frame until the sync comes back. </summary>
	private RealTimeSince _timeSinceOperatorPicksSent = 10f;

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
		UpdateSharing();
		UpdateTraining();
		if ( IsLocalPlayer )
		{
			var currentTag = GameSettingsSystem.Current?.ClanTag;
			if ( ClanTag != currentTag )
			{
				UpdateClanTag( currentTag ?? "" );
			}
			var operatorPicks = OperatorOutfits.LocalPicks;
			if ( OperatorPicks != operatorPicks && _timeSinceOperatorPicksSent > 1f )
			{
				_timeSinceOperatorPicksSent = 0f;
				UpdateOperatorPicks( operatorPicks );
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
