using Facepunch.UI;

namespace Facepunch;

public enum RadioSound
{
	/// <summary>
	/// When the round starts.
	/// </summary>
	RoundStarted,
	/// <summary>
	/// When the team has won.
	/// </summary>
	RoundWon,
	/// <summary>
	/// When the team has lost.
	/// </summary>
	RoundLost,
	/// <summary>
	/// When the bomb has been planted.
	/// </summary>
	BombPlanted,
	/// <summary>
	/// When the bomb has been defused.
	/// </summary>
	BombDefused,
	/// <summary>
	/// When someone has thrown a grenade.
	/// </summary>
	ThrownGrenade,
	/// <summary>
	/// When someone dies, and there's 2 people left.
	/// </summary>
	TwoEnemiesLeft,
	/// <summary>
	/// When someone dies, and there's 1 person left.
	/// </summary>
	OneEnemyLeft,
	/// <summary>
	/// When a teammate dies.
	/// </summary>
	TeammateDies
}

public class TeamRadioCategory
{
	[KeyProperty] public string Category { get; set; }
	[Property] public bool IsHidden { get; set; }

	public List<TeamRadioEntry> Entries { get; set; }

	public class TeamRadioEntry
	{
		[KeyProperty] public string Name { get; set; }
		[KeyProperty] public SoundEvent Sound { get; set; }
		[Property] public bool IsHidden { get; set; }
	}
}

[GameResource( "HC1/Radio Sounds", "radio", "" )]
public class RadioSounds : GameResource
{
	public static HashSet<RadioSounds> All { get; set; } = new();

	[Property, Group( "Setup" )] public Team Team { get; set; }

	[Property, Group( "Data" )] public Dictionary<RadioSound, SoundEvent> Sounds { get; set; }

	[Property, Group( "Data" )] public List<TeamRadioCategory> TeamSounds { get; set; }

	/// <summary>
	/// Played a team's voice line for a match event. The voice lines were deleted (the user, 2026-10-05), so it plays
	/// nothing: a compiled .radio left on a machine after its source went would otherwise still load and play them.
	/// </summary>
	public static void Play( Team team, RadioSound snd )
	{
	}

	/// <summary>
	/// Locally controlled, spam control.
	/// </summary>
	private static TimeSince TimeSinceRadio;

	/// <summary>
	/// How frequently can we spam the radio?
	/// </summary>
	private const float RadioSpamDelay = 2f;
	
	/// <summary>
	/// Send a radio sound to all players on the specified team
	/// </summary>
	/// <param name="team"></param>
	/// <param name="category"></param>
	/// <param name="sound"></param>
	public static void Play( Team team, string category, string sound )
	{
		var player = Client.Local.PlayerPawn;
		if ( player is null ) return;

		if ( player.HealthComponent.State != LifeState.Alive )
			return;

		// Only send this message to members of the specified team. It's the callout's text in team chat: its voice
		// line was deleted with the rest.
		using ( Rpc.FilterInclude( GameUtils.GetPlayers( team ).Select( x => x.Connection ) ) )
		{
			Chat.Instance?.AddText( sound, Chat.ChatModes.Team, "radio" );
		}
	}

	[ConCmd( "radio_sound" )]
	public static void CmdPlay( string category, string sound )
	{
		if ( TimeSinceRadio < RadioSpamDelay && TimeSinceRadio > 0f )
			return;
		
		TimeSinceRadio = 0f;

		var team = Client.Local.Team;
		Play( team, category, sound );
	}

	protected override void PostLoad()
	{
		if ( All.Add( this ) ) return;
		Log.Warning( "Tried to add two of the same radio sounds (?)" );
	}
}
