using Sandbox.Audio;

namespace Facepunch;

public enum GameLanguage
{
	[Title( "English (UK)" )]
	EnglishUK,
	[Title( "English (US)" )]
	EnglishUS
}

public enum VoiceChatMode
{
	[Title( "Auto (GameMode Default)" )]
	Auto,
	[Title( "Global (Whole Lobby)" )]
	Global,
	[Title( "Team Only" )]
	TeamOnly,
	[Title( "Party Only" )]
	PartyOnly
}

public class GameSettings
{
	public static GameLanguage GetDefaultLanguage()
	{
		try
		{
			var name = System.Globalization.CultureInfo.CurrentCulture.Name;
			if ( name.EndsWith( "US", System.StringComparison.OrdinalIgnoreCase ) )
				return GameLanguage.EnglishUS;
		}
		catch { }
		return GameLanguage.EnglishUK;
	}

	[Title( "Language" ), Description( "The language to use for text in the game" ), Group( "Game" ), Icon( "language" )]
	public GameLanguage Language { get; set; } = GameLanguage.EnglishUK;

	[Title( "Clan Tag" ), Description( "A short tag prepended to your name" ), Group( "Game" )]
	public string ClanTag { get; set; } = "";

	[Title( "Field Of View" ), Description( "Effects the camera's vision." ), Group( "Video" ), Icon( "grid_view" ), Range( 65, 110, 1 )]
	public float FieldOfView { get; set; } = 85;

	[Title( "Picture-In-Picture Scopes" ), Description( "Render live 3D scope lenses. Turn this off if scoped weapons cause render artifacts or performance issues." ), Group( "Video" ), Icon( "center_focus_strong" )]
	public bool PictureInPictureScopes { get; set; } = true;

	[Title( "Master" ), Description( "The overall volume" ), Group( "Volume" ), Icon( "grid_view" ), Range( 0, 100, 5 )]
	public float MasterVolume { get; set; } = 100;

	[Title( "Music" ), Description( "How loud any music will play" ), Group( "Volume" ), Icon( "grid_view" ), Range( 0, 100, 5 )]
	public float MusicVolume { get; set; } = 100;

	[Title( "SFX" ), Description( "Most effects in the game" ), Group( "Volume" ), Icon( "grid_view" ), Range( 0, 100, 5 )]
	public float SFXVolume { get; set; } = 100;

	[Title( "UI" ), Description( "interface sounds" ), Group( "Volume" ), Icon( "grid_view" ), Range( 0, 100, 5 )]
	public float UIVolume { get; set; } = 100;

	[Title( "Radio" ), Description( "" ), Group( "Volume" ), Icon( "grid_view" ), Range( 0, 100, 5 )]
	public float RadioVolume { get; set; } = 100;

	[Title( "Voice" ), Description( "" ), Group( "Volume" ), Icon( "grid_view" ), Range( 0, 100, 5 )]
	public float VoiceVolume { get; set; } = 100;

	[Title( "Voice Chat" ), Description( "Enable or disable in-game voice chat" ), Group( "Voice" )]
	public bool VoiceEnabled { get; set; } = true;

	[Title( "Push To Talk" ), Description( "Requires holding key to transmit voice" ), Group( "Voice" )]
	public bool VoicePushToTalk { get; set; } = true;

	[Title( "Proximity Voice" ), Description( "Voice chat is 3D spatialized and audible to nearby players" ), Group( "Voice" )]
	public bool VoiceProximity { get; set; } = false;

	[Title( "Voice Chat Mode" ), Description( "Who can hear your voice (if proximity is off)" ), Group( "Voice" )]
	public VoiceChatMode VoiceChatMode { get; set; } = VoiceChatMode.Auto;

	[Title( "Death Comms" ), Description( "Hear the reaction of players you kill for a brief moment" ), Group( "Voice" )]
	public bool VoiceDeathComms { get; set; } = true;

	[Title( "Profanity Filter" ), Description( "Filters offensive language in text chat" ), Group( "Chat" )]
	public bool ProfanityFilter { get; set; } = true;

	[Title( "View Bob" ), Group( "Game" ), Range( 0, 100, 5f )]
	public float ViewBob { get; set; } = 100f;

	[Title( "Aim Assist" ), Description("Pulls your aim towards targets while using a controller"), Group( "Controls" )]
	public bool AimAssist { get; set; } = true;

	[Title( "Aim Input" ), Group( "Controls" )]
	public bool ToggleAim { get; set; } = false;

	[Title( "Sprint Input" ), Group( "Controls" )]
	public bool ToggleSprint { get; set; } = false;

	[Title( "Scorestreaks" ), Description( "When on, your streak meter carries across deaths and charges from score (kills + objectives). When off, streaks count consecutive kills and reset on death." ), Group( "Game" ), Icon( "bolt" )]
	public bool UseScorestreaks { get; set; } = false;

	[Title( "Show Dot" ), Group( "Crosshair" )]
	public bool ShowCrosshairDot { get; set; } = true;

	[Title( "Dynamic" ), Group( "Crosshair" )]
	public bool DynamicCrosshair { get; set; } = true;

	[Title( "Length" ), Group( "Crosshair" ), Range( 2, 50, 1 )]
	public float CrosshairLength { get; set; } = 10;

	[Title( "Width" ), Group( "Crosshair" ), Range( 1, 10, 1 )]
	public float CrosshairWidth { get; set; } = 2;

	[Title( "Distance" ), Group( "Crosshair" ), Range( -5, 50, 0.1f )]
	public float CrosshairDistance { get; set; } = 15;

	[Title( "Color" ), Group( "Crosshair" )]
	public Color CrosshairColor { get; set; } = Color.White;
}

public partial class GameSettingsSystem
{
	private static GameSettings current { get; set; }
	public static GameSettings Current
	{
		get
		{
			if ( current is null ) Load();
			return current;
		}
		set
		{
			current = value;
		}
	}

	public static string FilePath => "gamesettings.json";

	/// <summary>
	/// Pushes the saved volume settings onto the audio mixer. Safe to call any time —
	/// if the mixer isn't ready yet it's a no-op and will be re-applied on the next call.
	/// Called on Save, on Load, and at scene startup (HUD / main menu) so muted audio
	/// stays muted across play sessions in the editor.
	/// </summary>
	public static void ApplyVolumes()
	{
		try
		{
			if ( Mixer.Master is null )
				return;

			Mixer.Master.Volume = Current.MasterVolume / 100f;

			var channel = Mixer.Master.GetChildren();
			channel[0].Volume = Current.MusicVolume / 100f;
			channel[1].Volume = Current.SFXVolume / 100f;
			channel[2].Volume = Current.UIVolume / 100f;
			channel[3].Volume = Current.RadioVolume / 100f;
			channel[4].Volume = Current.VoiceEnabled ? (Current.VoiceVolume / 100f) : 0f;
		}
		catch ( Exception )
		{
			// Mixer not initialised yet; volumes will be applied again on the next load/save/startup.
		}
	}

	/// <summary>
	/// Applies the current (possibly unsaved) settings live, so changes preview immediately
	/// in the settings menu — e.g. dragging a volume slider is heard right away.
	/// </summary>
	public static void Apply()
	{
		ApplyVolumes();

		// Push the streak preference to the live PlayerScore so it takes effect immediately
		// if the player is currently in a match and changes it mid-game.
		var localScore = Client.Local?.GetComponent<Facepunch.UI.PlayerScore>();
		if ( localScore.IsValid() )
			localScore.UseScorestreaks = Current.UseScorestreaks;
	}

	public static void Save()
	{
		Apply();
		FileSystem.Data.WriteJson( FilePath, Current );
	}

	public static void Load()
	{
		if ( !FileSystem.Data.FileExists( FilePath ) )
		{
			Current = new GameSettings();
			Current.Language = GameSettings.GetDefaultLanguage();
		}
		else
		{
			Current = FileSystem.Data.ReadJson<GameSettings>( FilePath, new() );
		}
		ApplyVolumes();
	}
}
