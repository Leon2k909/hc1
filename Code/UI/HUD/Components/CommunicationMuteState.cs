using System.Collections.Generic;

namespace Facepunch;

public static class CommunicationMuteState
{
	private static readonly HashSet<string> TextMutedPlayers = new();
	private static readonly HashSet<string> VoiceMutedPlayers = new();
	private static readonly HashSet<string> LoadedPlayers = new();
	private static ulong? _accountId;
	private static int _version;

	public static int Version
	{
		get
		{
			EnsureAccount();
			return _version;
		}
	}

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
		SetMuted( TextMutedPlayers, client, !IsTextMuted( client ), "text" );
	}

	public static void ToggleVoice( Client client )
	{
		SetMuted( VoiceMutedPlayers, client, !IsVoiceMuted( client ), "voice" );
	}

	private static bool IsMuted( HashSet<string> mutedPlayers, Client client )
	{
		EnsureLoaded( client );
		var key = GetKey( client );
		return !string.IsNullOrEmpty( key ) && mutedPlayers.Contains( key );
	}

	private static void SetMuted( HashSet<string> mutedPlayers, Client client, bool muted, string channel )
	{
		if ( !CanMute( client ) )
			return;

		var key = GetKey( client );
		if ( string.IsNullOrEmpty( key ) )
			return;

		var changed = muted ? mutedPlayers.Add( key ) : mutedPlayers.Remove( key );
		if ( changed )
		{
			_version++;
			// Connection-only identities stay temporary; Steam identities survive restarts.
			if ( Game.SteamId != 0 && client.SteamId != 0 )
				Game.Cookies.Set( CookieKey( client, channel ), muted );
		}
	}

	private static void EnsureAccount()
	{
		if ( _accountId == Game.SteamId ) return;
		_accountId = Game.SteamId;
		TextMutedPlayers.Clear();
		VoiceMutedPlayers.Clear();
		LoadedPlayers.Clear();
		_version++;
	}

	private static void EnsureLoaded( Client client )
	{
		EnsureAccount();
		if ( !client.IsValid() || Game.SteamId == 0 || client.SteamId == 0 ) return;

		var key = GetKey( client );
		if ( !LoadedPlayers.Add( key ) ) return;

		// Voice packets and scoreboard rows can ask repeatedly: read each player's cookies once per account.
		var textMuted = Game.Cookies.Get( CookieKey( client, "text" ), false );
		var voiceMuted = Game.Cookies.Get( CookieKey( client, "voice" ), false );
		if ( textMuted ) TextMutedPlayers.Add( key );
		if ( voiceMuted ) VoiceMutedPlayers.Add( key );
		if ( textMuted || voiceMuted ) _version++;
	}

	private static string CookieKey( Client client, string channel ) =>
		$"hc1.comms.mute.v1.{Game.SteamId}.{client.SteamId}.{channel}";

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
