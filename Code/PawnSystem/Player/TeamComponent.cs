using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A component that has a team on it.
/// </summary>
public interface ITeam : IValid
{
	public Team Team { get; set; }
}

public enum Team
{
	Unassigned = 0,

	Terrorist,
	CounterTerrorist
}

public record TeamChangedEvent( Team Before, Team After ) : IGameEvent;

public static class TeamExtensions
{
	/// <summary>
	/// Accessor to get the team of someone/something.
	/// </summary>
	/// <param name="gameObject"></param>
	/// <returns></returns>
	public static Team GetTeam( this GameObject gameObject )
	{
		if ( gameObject.Root.GetComponent<ITeam>() is { IsValid: true } team )
		{
			return team.Team;
		}

		if ( gameObject.Root.GetComponent<Pawn>() is { IsValid: true } pawn )
		{
			return pawn.Team;
		}

		if ( gameObject.Root.GetComponent<Client>() is { IsValid: true } state )
		{
			return state.Team;
		}

		return Team.Unassigned;
	}

	//
	// For all of this, maybe the gamemode should be controlling it, and not some global methods
	//

	/// <summary>
	/// Are we friendly with this other team?
	/// </summary>
	/// <param name="teamOne"></param>
	/// <param name="teamTwo"></param>
	/// <returns></returns>
	private static bool IsFriendly( Team teamOne, Team teamTwo )
	{
		if ( teamOne == Team.Unassigned || teamTwo == Team.Unassigned ) return false;
		return teamOne == teamTwo;
	}

	/// <summary>
	/// Are these two GameObjects friends with eachother?
	/// </summary>
	/// <param name="self"></param>
	/// <param name="other"></param>
	/// <returns></returns>
	public static bool IsFriendly( this GameObject self, GameObject other )
	{
		if ( !self.IsValid() || !other.IsValid() ) return false;
		return IsFriendly( self.GetTeam(), other.GetTeam() );
	}

	/// <summary>
	/// Are these two <see cref="PlayerPawn"/>s friends with each other?
	/// </summary>
	public static bool IsFriendly( this PlayerPawn self, PlayerPawn other )
	{
		if ( !self.IsValid() || !other.IsValid() ) return false;
		return IsFriendly( self.Team, other.Team );
	}

	/// <summary>
	/// Are these two <see cref="Client"/>s friends with each other?
	/// </summary>
	public static bool IsFriendly( this Client self, Client other )
	{
		if ( !self.IsValid() || !other.IsValid() ) return false;
		return IsFriendly( self.Team, other.Team );
	}

	/// <summary>
	/// The teams are Red Team and Blue Team. The enum keeps its old Terrorist/CounterTerrorist names because scenes and
	/// prefabs store them.
	/// </summary>
	public static string GetName( this Team team )
	{
		return team switch
		{
			Team.Terrorist => "Red Team",
			Team.CounterTerrorist => "Blue Team",
			_ => "Unassigned",
		};
	}

	/// <summary>
	/// A team's colour means that team everywhere, to every viewer: enemy markers are the enemy's team colour rather than
	/// a generic enemy red, which would look like Red Team's teammates. Red is the logo's pure red (green and blue level):
	/// with more green than blue it read as orange.
	/// </summary>
	public static Color GetColor( this Team team )
	{
		return team switch
		{
			Team.CounterTerrorist => new Color32( 5, 146, 235 ),
			Team.Terrorist => new Color32( 228, 32, 40 ),
			_ => new Color32( 255, 255, 255 ),
		};
	}

	/// <summary> The team logo (Tools/team_logos.py builds it and the banner from the source art). </summary>
	public static string GetIconPath( this Team team )
	{
		return team switch
		{
			Team.CounterTerrorist => "/ui/teams/blue_team_logo.png",
			Team.Terrorist => "/ui/teams/red_team_logo.png",
			_ => ""
		};
	}

	public static string GetBannerPath( this Team team )
	{
		return team switch
		{
			Team.CounterTerrorist => "/ui/teams/blue_team_logo_banner.png",
			Team.Terrorist => "/ui/teams/red_team_logo_banner.png",
			_ => ""
		};
	}

	public static Team GetOpponents( this Team team )
	{
		return team switch
		{
			Team.CounterTerrorist => Team.Terrorist,
			Team.Terrorist => Team.CounterTerrorist,
			_ => Team.Unassigned
		};
	}
}
