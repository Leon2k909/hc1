using Sandbox.Events;
using Sandbox.Network;

namespace Facepunch;

/// <summary>Settings for the custom game being started (CreateLobbyPage), cleared when the main menu is opened again.</summary>
public sealed class CustomGameSettings
{
	public static CustomGameSettings Current { get; private set; }

	public int PlayerLimit { get; private init; }
	public bool FillWithBots { get; private init; }

	/// <summary>Public games are listed in the server browser (SESSIONS); Friends and Invite Only games aren't.</summary>
	public LobbyPrivacy Privacy { get; private init; }

	/// <summary>The match rules picked on the page's RULES and PLAYER tabs. They hold for every map the lobby plays.</summary>
	public CustomGameRules Rules { get; private init; } = new();

	public static void Configure( int playerLimit, bool fillWithBots, LobbyPrivacy privacy, CustomGameRules rules = null )
	{
		Current = new()
		{
			PlayerLimit = Math.Clamp( playerLimit, 2, 10 ),
			FillWithBots = fillWithBots,
			Privacy = privacy,
			Rules = rules?.Clone() ?? new()
		};
	}

	public static void Reset() => Current = null;

	/// <summary>The rules in force: the custom game's, or the defaults (every rule as the modes have it) in any other match.</summary>
	public static CustomGameRules ActiveRules => Current?.Rules ?? CustomGameRules.Defaults;

	public LobbyConfig CreateLobbyConfig() => new()
	{
		Name = LobbyName,
		Privacy = Privacy,
		MaxPlayers = PlayerLimit,
		DestroyWhenHostLeaves = true
	};

	/// <summary>What the server browser lists it as, so players can tell whose game it is.</summary>
	private static string LobbyName
	{
		get
		{
			var host = Connection.Local?.DisplayName;
			return string.IsNullOrWhiteSpace( host ) ? "Razed Custom Game" : $"{host}'s Custom Game";
		}
	}

	/// <summary>
	/// Host, from <see cref="GameMode"/>'s OnStart: puts the limits into the mode's own components before play starts.
	/// The rest of the rules are read where they apply (<see cref="ActiveRules"/>).
	/// </summary>
	public static void ApplyTo( GameMode mode )
	{
		if ( Current?.Rules is not { } rules || !mode.IsValid() || !Networking.IsHost )
			return;

		const FindMode everything = FindMode.EverythingInSelfAndDescendants;

		// The time limit is the play state's own length. "No limit" never leaves it (DisplayedTime then shows no clock).
		if ( rules.TimeLimit is { } time )
		{
			foreach ( var state in mode.Components.GetAll<StateComponent>( everything ) )
			{
				if ( IsTimedPlayState( state ) )
					state.DefaultDuration = time > 0f ? time : float.PositiveInfinity;
			}
		}

		if ( rules.ScoreLimit is { } score )
		{
			var wins = mode.Components.GetAll<TeamEarlyWinCondition>( everything ).ToList();
			var roundLimits = mode.Components.GetAll<RoundLimit>( everything ).ToList();

			// Defuse: the rounds to win, with twice as many rounds at most (the prefab's 6 of 12), so the half falls at
			// the target. Retakes has no win score, only its round limit.
			foreach ( var win in wins )
				win.TargetScore = score > 0 ? score : int.MaxValue;

			if ( score > 0 )
			{
				foreach ( var limit in roundLimits )
					limit.MaxRounds = wins.Count > 0 ? score * 2 : score;
			}
		}

		if ( rules.RespawnDelay is { } delay )
		{
			foreach ( var respawner in mode.Components.GetAll<Respawner>( everything ) )
				respawner.RespawnDelaySeconds = delay;
		}

		Log.Info( $"Custom game rules: {rules}" );
	}

	/// <summary>The play state of a mode with a time limit: TDM's, Deathmatch's, Domination's and the rest have a "Play Game"
	/// state that ends after its DefaultDuration. Defuse's, Retakes' and Cash Grab's last 0 (they end by score or rounds).</summary>
	public static bool IsTimedPlayState( StateComponent state ) =>
		state.IsValid() && state.GameObject.Name == "Play Game" && state.DefaultDuration > 0f && state.DefaultNextState is not null;

	/// <summary>Host: a soldier's max health under the rules, players at each spawn and bots as they're made. Synced.</summary>
	public static void ApplyMaxHealth( HealthComponent health )
	{
		if ( !Networking.IsHost || !health.IsValid() || Current?.Rules is not { } rules )
			return;

		health.MaxHealth = rules.MaxHealth;
	}
}

/// <summary>How fast health comes back after a hit (PlayerPawn.UpdateHealthRegen).</summary>
public enum HealthRegen
{
	Normal,
	Fast,
	Slow,
	Off
}

/// <summary>The skill bots roll (LightweightCombatBot.RollSkill).</summary>
public enum BotDifficulty
{
	Mixed,
	Recruit,
	Regular,
	Hardened,
	Veteran
}

/// <summary>
/// A custom game's match rules, after CoD's private match options. Null limits keep the mode's own, and the defaults
/// are every rule as a normal match has it, so a custom game left alone plays like Quick Play.
/// </summary>
public sealed class CustomGameRules
{
	public static readonly CustomGameRules Defaults = new();

	/// <summary>The players' health at full (HealthComponent.MaxHealth). Hardcore's hits scale with it (HealthComponent.Wounds.cs).</summary>
	public const float DefaultMaxHealth = 100f;

	/// <summary>Seconds of play: null keeps the mode's, 0 is no limit.</summary>
	public float? TimeLimit { get; set; }

	/// <summary>The score to win (Defuse: rounds to win; Retakes: the rounds played): null keeps the mode's, 0 is none.</summary>
	public int? ScoreLimit { get; set; }

	/// <summary>Seconds dead before a respawn, players and bots: null keeps the mode's.</summary>
	public float? RespawnDelay { get; set; }

	public float MaxHealth { get; set; } = DefaultMaxHealth;
	public HealthRegen Regen { get; set; } = HealthRegen.Normal;

	/// <summary>Bullets hurt only where they hit the head or neck. Knives, blasts and fire still hurt anywhere.</summary>
	public bool HeadshotsOnly { get; set; }

	/// <summary>Teammates' bullets, blades, blasts and fire hurt each other, as in every hardcore match. Your own still hurt you.</summary>
	public bool FriendlyFire { get; set; } = true;

	public BotDifficulty BotDifficulty { get; set; } = BotDifficulty.Mixed;

	/// <summary>The delay before a regenerating soldier starts to heal, and how fast (HP a second); no regen gives null.</summary>
	public (float Delay, float Rate)? RegenSpeed => Regen switch
	{
		HealthRegen.Fast => (2f, 50f),
		HealthRegen.Slow => (8f, 10f),
		HealthRegen.Off => null,
		_ => (4f, 25f)
	};

	public CustomGameRules Clone() => new()
	{
		TimeLimit = TimeLimit,
		ScoreLimit = ScoreLimit,
		RespawnDelay = RespawnDelay,
		MaxHealth = MaxHealth,
		Regen = Regen,
		HeadshotsOnly = HeadshotsOnly,
		FriendlyFire = FriendlyFire,
		BotDifficulty = BotDifficulty
	};

	public override string ToString() =>
		$"time {TimeLimit?.ToString() ?? "default"}, score {ScoreLimit?.ToString() ?? "default"}, " +
		$"respawn {RespawnDelay?.ToString() ?? "default"}, health {MaxHealth}, regen {Regen}, headshots only {HeadshotsOnly}, " +
		$"friendly fire {FriendlyFire}, bots {BotDifficulty}";
}
