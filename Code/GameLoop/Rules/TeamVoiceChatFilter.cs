namespace Facepunch;

/// <summary>
/// Filters voice chat to teams, so players on a team can only hear each other.
/// </summary>
public partial class TeamVoiceChatFilter : Component, IVoiceFilter
{
	/// <summary>
	/// The local player's Voice Chat Mode, with Auto settled: Team Only in Defuse and Retakes, else Global. The HUD's
	/// voice list (<see cref="Facepunch.UI.Voices"/>) shows it on your own row, so change them together.
	/// </summary>
	public static VoiceChatMode ActiveMode
	{
		get
		{
			var mode = GameSettingsSystem.Current.VoiceChatMode;
			if ( mode != VoiceChatMode.Auto )
				return mode;

			var ident = GameMode.Instance?.Ident;
			return ident is "defuse" or "tactical_defuse" or "retakes" ? VoiceChatMode.TeamOnly : VoiceChatMode.Global;
		}
	}

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
		var mode = ActiveMode;

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
