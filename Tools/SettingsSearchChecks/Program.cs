global using Sandbox;
using Facepunch;
using Facepunch.UI;

var checks = 0;
void Check( bool condition, string message )
{
	if ( !condition ) throw new Exception( message );
	checks++;
}
void Matches( string query, bool expected, params string[] texts ) => Check(
	SettingsSearch.Matches( SettingsSearch.Words( query ), texts ) == expected,
	$"Search '{query}' against '{string.Join( " | ", texts )}' should match: {expected}" );

Matches( "fov", true, "Field Of View", "Video" );
Matches( "ads fov", true, "ADS Field Of View", "Video" );
Matches( "third person fov", true, "Third Person Field Of View" );
Matches( "gamepad sens", true, "Controller Horizontal Sensitivity", "Controls" );
Matches( "mouse sens", true, "Mouse Sensitivity" );
Matches( "aim down sights sensitivity", true, "Mouse ADS Sensitivity" );
Matches( "ads", true, "Aim Down Sights", "Weapon Handling", "mouse2" );
Matches( "ptt", true, "Push To Talk", "Voice" );
Matches( "pip", true, "Picture-In-Picture Scopes", "Video" );
Matches( "picture in picture", true, "Picture-In-Picture Scopes" );
Matches( "sound effects", true, "SFX", "Volume" );
Matches( "sfx", true, "Sound Effects", "Volume" );
Matches( "user interface volume", true, "UI", "Volume" );
Matches( "colour", true, "Color", "Crosshair" );
Matches( "color", true, "Colour", "Crosshair" );
Matches( "theatre", true, "Theater Recording" );
Matches( "theater", true, "Theatre Recording" );
Matches( "  MOUSE\tADS\nSensitivity  ", true, "Mouse ADS Sensitivity" );
Matches( "field-of-view", true, "Field Of View" );
Matches( "field_of_view", true, "Field Of View" );
Matches( "field–of–view", true, "Field Of View" );
Matches( "crosshair\u00a0colour", true, "Color", "Crosshair" );
Matches( "space", true, "Jump", "Movement", "space" );
Matches( "shift + w", true, "Sprint", "Movement", "shift + w" );
Matches( "+", true, "Keybinds", "+" );
Matches( "=", true, "Keybinds", "=" );
Matches( "fov volume", false, "Field Of View", "Video" );
Matches( "gamepad mouse", false, "Mouse Sensitivity" );
Matches( "pip", false, "Pipe Climbing" );
Matches( "user interface", false, "Build Weapon" );
Matches( "sound effects", false, "Voice Chat" );
Matches( "", false, "Field Of View" );
Matches( null, false, "Field Of View" );
Matches( "\t\n  ", false, "Field Of View" );
Matches( "missing", false, null, "" );
Matches( "francais", true, "Français" );
Check( !SettingsSearch.Matches( null, "Field Of View" ), "Null search words must not match." );

GameText.Translations["Field Of View"] = "Champ de vision";
GameText.Translations["Video"] = "Vidéo";
var property = new PropertyDescription { Title = "Field Of View", Group = "Video" };
Check( SettingsSearch.Matches( SettingsSearch.Words( "champ video" ), property ), "Translated names and groups must remain searchable." );
Check( SettingsSearch.Matches( SettingsSearch.Words( "fov" ), property ), "English aliases must work with translated properties." );

Console.WriteLine( $"PASS: {checks} settings search checks against production SettingsSearch." );

// The search itself is linked from production; only engine metadata and translation services are supplied here.
namespace Sandbox
{
	public class PropertyDescription { public string Title { get; set; } public string Group { get; set; } }
}
namespace Facepunch
{
	public static class GameText
	{
		public static Dictionary<string, string> Translations { get; } = new();
		public static string Get( string text ) => text is null ? "" : Translations.GetValueOrDefault( text, text );
	}
}
namespace Facepunch.UI
{
	public static class LanguageMenu
	{
		// Same accent table as the existing language picker, independent of any UI framework.
		private const string Accented = "àáâãäåçèéêëìíîïıñòóôõöøùúûüýÿşğłńśźżćęą";
		private const string Plain = "aaaaaaceeeeiiiiinoooooouuuuyysglnszzcea";
		public static string Fold( string text ) => new( text.ToLowerInvariant().Select( c =>
		{
			var index = Accented.IndexOf( c );
			return index >= 0 ? Plain[index] : c;
		} ).ToArray() );
	}
}
