using Sandbox.Audio;

namespace Facepunch;

public enum GameLanguage
{
	[Title( "English (UK)" )]
	EnglishUK,
	[Title( "English (US)" )]
	EnglishUS,
	[Title( "Français" )]
	French,
	[Title( "Deutsch" )]
	German,
	[Title( "Español" )]
	Spanish,
	[Title( "Português (Brasil)" )]
	PortugueseBrazil,

	// These have a table each (Code/Settings/Text/Languages). A new language goes last, since GameText.Current's range
	// ends at the last one.
	[Title( "Italiano" )]
	Italian,
	[Title( "Polski" )]
	Polish,
	[Title( "Русский" )]
	Russian,
	[Title( "Українська" )]
	Ukrainian,
	[Title( "Türkçe" )]
	Turkish,
	[Title( "日本語" )]
	Japanese,
	[Title( "한국어" )]
	Korean,
	[Title( "简体中文" )]
	ChineseSimplified,
	[Title( "繁體中文" )]
	ChineseTraditional
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

/// <summary>
/// Shows a bool setting as a switch between two named options instead of a checkbox (<c>SettingEntry</c>): the first
/// is false, the second true.
/// </summary>
[AttributeUsage( AttributeTargets.Property )]
public sealed class ChoicesAttribute : Attribute
{
	public string WhenFalse { get; }
	public string WhenTrue { get; }

	public ChoicesAttribute( string whenFalse, string whenTrue )
	{
		WhenFalse = whenFalse;
		WhenTrue = whenTrue;
	}
}

public class GameSettings
{
	public static GameLanguage GetDefaultLanguage()
	{
		try
		{
			var name = System.Globalization.CultureInfo.CurrentCulture.Name;
			if ( name.StartsWith( "fr", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.French;
			if ( name.StartsWith( "de", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.German;
			if ( name.StartsWith( "es", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Spanish;
			if ( name.StartsWith( "pt", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.PortugueseBrazil;
			if ( name.StartsWith( "it", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Italian;
			if ( name.StartsWith( "pl", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Polish;
			if ( name.StartsWith( "ru", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Russian;
			if ( name.StartsWith( "uk", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Ukrainian;
			if ( name.StartsWith( "tr", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Turkish;
			if ( name.StartsWith( "ja", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Japanese;
			if ( name.StartsWith( "ko", StringComparison.OrdinalIgnoreCase ) ) return GameLanguage.Korean;
			if ( name.StartsWith( "zh", StringComparison.OrdinalIgnoreCase ) )
			{
				// Taiwan, Hong Kong and Macau write traditional characters, the mainland and Singapore simplified.
				var culture = name.ToUpperInvariant();
				var traditional = !culture.Contains( "HANS" ) && (culture.Contains( "HANT" )
					|| culture.EndsWith( "TW" ) || culture.EndsWith( "HK" ) || culture.EndsWith( "MO" ));
				return traditional ? GameLanguage.ChineseTraditional : GameLanguage.ChineseSimplified;
			}
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

	[Title( "Field Of View" ), Description( "How wide you see in first person, in degrees across the screen." ), Group( "Video" ), Icon( "grid_view" ), Range( 60, 120, 1 )]
	public float FieldOfView { get; set; } = 85;

	// Equipment.AimFov. Affected (false) is the default, as in CoD.
	[Title( "ADS Field Of View" ), Description( "Affected: aiming zooms your own field of view, so a wider one stays wider while aiming. Independent: aiming always zooms to the same view, whatever your field of view." ), Group( "Video" ), Icon( "center_focus_weak" ), Choices( "Affected", "Independent" )]
	public bool IndependentAdsFov { get; set; } = false;

	// Read through the property: a settings file or a hotloaded settings object from before it existed has 0.
	[Title( "Third Person Field Of View" ), Description( "How wide you see from behind a player: the deathcam and spectating in third person." ), Group( "Video" ), Icon( "videocam" ), Range( 60, 120, 1 )]
	public float ThirdPersonFieldOfView { get => thirdPersonFov > 0f ? thirdPersonFov : 85f; set => thirdPersonFov = value; }
	private float thirdPersonFov;

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

	// Stored inverted so it's on by default even on a settings object from before it existed: a hotload leaves new
	// fields at false rather than running their initialisers.
	[Title( "Corner Slicing" ), Description( "Black Ops 6-style: aiming down sights by a corner tilts your gun towards the opening. Only in your own view: your character, hitbox and shots don't change." ), Group( "Game" ), Icon( "rotate_right" )]
	public bool CornerSlicing { get => !plainCorners; set => plainCorners = !value; }
	private bool plainCorners;

	// Stored inverted too, so it's on by default.
	[Title( "Theater Recording" ), Description( "Records each match you play, so you can watch it again in the Theater. Only the soldiers are recorded, a few times a second." ), Group( "Game" ), Icon( "movie" )]
	public bool TheaterRecording { get => !noTheaterRecording; set => noTheaterRecording = !value; }
	private bool noTheaterRecording;

	// Stored inverted too, so it's on by default: the markers over teammates' heads are only their circles
	// (PlayerMarkerPanel, LightweightBotMarkerPanel).
	[Title( "Hide Teammate Names" ), Description( "Shows only the circle over your teammates' heads, without their names, health or weapons. A teammate carrying the bomb still has the bomb icon." ), Group( "Game" ), Icon( "label_off" )]
	public bool HideTeammateNames { get => !showTeammateNames; set => showTeammateNames = !value; }
	private bool showTeammateNames;

	[Title( "Aim Assist" ), Description("Pulls your aim towards targets while using a controller"), Group( "Controls" )]
	public bool AimAssist { get; set; } = true;

	[Title( "Aim Input" ), Group( "Controls" )]
	public bool ToggleAim { get; set; } = false;

	[Title( "Sprint Input" ), Group( "Controls" )]
	public bool ToggleSprint { get; set; } = false;

	[Title( "Streak Type" ), Description( "Kills: rewards come from kills in a row and reset on death. Score: rewards charge from score (kills + objectives) and carry across deaths." ), Group( "Game" ), Icon( "bolt" ), Choices( "Kills", "Score" )]
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
		// if the player is currently in a match and changes it mid-game. Client.Local outlives its match (a destroyed
		// client isn't null), so ?. let the menu's language picker throw here and skip saving.
		var local = Client.Local;
		var localScore = local.IsValid() ? local.GetComponent<Facepunch.UI.PlayerScore>() : null;
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
