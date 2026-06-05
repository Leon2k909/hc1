namespace Facepunch;

/// <summary>
/// Filters voice chat to teams, so players on a team can only hear each other.
/// </summary>
public partial class TeamVoiceChatFilter : Component, IVoiceFilter
{
	private bool DontSendFilter( Client player )
	{
		// Send voices to spectators
		if ( player.Team == Team.Unassigned ) return false;

		// Death Comms check: if Client.Local (speaker) was recently killed by player (listener), let them hear!
		if ( Client.Local.IsValid() && Client.Local.HasActiveDeathCommTo( player ) )
		{
			return false; // Do not exclude!
		}

		// Proximity Voice check: if proximity is enabled, filter connections based on distance
		if ( GameSettingsSystem.Current.VoiceProximity )
		{
			var localPawn = Client.Local?.PlayerPawn;
			var remotePawn = player.PlayerPawn;
			if ( localPawn.IsValid() && remotePawn.IsValid() )
			{
				return localPawn.WorldPosition.Distance( remotePawn.WorldPosition ) > 1200f;
			}
			return true;
		}

		// Don't send to enemies if Team Only Voice is enabled
		var mode = GameSettingsSystem.Current.VoiceChatMode;

		if ( mode == VoiceChatMode.Auto )
		{
			var ident = GameMode.Instance?.Ident;
			if ( ident == "defuse" || ident == "retakes" )
			{
				mode = VoiceChatMode.TeamOnly;
			}
			else
			{
				mode = VoiceChatMode.Global;
			}
		}

		if ( mode == VoiceChatMode.PartyOnly )
		{
			if ( PartySystem.Current.IsValid() && PartySystem.Current.LocalIsInParty && player.Connection is not null )
			{
				return !PartySystem.Current.IsInParty( player.Connection.Id );
			}
			// If not in a party, exclude everyone else (only talk to yourself)
			return player != Client.Local;
		}
		else if ( mode == VoiceChatMode.TeamOnly )
		{
			return !player.IsFriendly( Client.Local );
		}

		// Otherwise, everyone can hear everyone (Global Lobby Chat)
		return false;
	}

	IEnumerable<Connection> IVoiceFilter.GetExcludeFilter()
	{
		return Scene.GetAllComponents<Client>()
			.Where( DontSendFilter )
			.Select( x => x.Connection );
	}
}
