using System.Collections.Generic;

namespace Facepunch;

public static class CommunicationMuteState
{
	private static readonly HashSet<string> TextMutedPlayers = new();
	private static readonly HashSet<string> VoiceMutedPlayers = new();

	public static int Version { get; private set; }

	public static bool CanMute( Client client )
	{
		return client.IsValid() && !client.IsLocalPlayer && !client.IsBot;
	}

	public static bool IsTextMuted( Client client )
	{
		return IsMuted( TextMutedPlayers, client );
	}

	public static bool IsVoiceMuted( Client client )
	{
		return IsMuted( VoiceMutedPlayers, client );
	}

	public static void ToggleText( Client client )
	{
		SetMuted( TextMutedPlayers, client, !IsTextMuted( client ) );
	}

	public static void ToggleVoice( Client client )
	{
		SetMuted( VoiceMutedPlayers, client, !IsVoiceMuted( client ) );
	}

	private static bool IsMuted( HashSet<string> mutedPlayers, Client client )
	{
		var key = GetKey( client );
		return !string.IsNullOrEmpty( key ) && mutedPlayers.Contains( key );
	}

	private static void SetMuted( HashSet<string> mutedPlayers, Client client, bool muted )
	{
		if ( !CanMute( client ) )
			return;

		var key = GetKey( client );
		if ( string.IsNullOrEmpty( key ) )
			return;

		var changed = muted ? mutedPlayers.Add( key ) : mutedPlayers.Remove( key );
		if ( changed )
		{
			Version++;
		}
	}

	private static string GetKey( Client client )
	{
		if ( !client.IsValid() )
			return null;

		if ( client.SteamId != 0 )
			return $"steam:{client.SteamId}";

		if ( client.Connection is not null )
			return $"connection:{client.Connection.Id}";

		return $"client:{client.Id}";
	}
}