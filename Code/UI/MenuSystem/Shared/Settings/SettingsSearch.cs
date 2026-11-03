namespace Facepunch.UI;

/// <summary>
/// The settings page's search: a setting or keybind matches when every word of the search is in its name, in the
/// player's language or in English, or in its category's name. Case, accents, whitespace and hyphens don't count.
/// </summary>
public static class SettingsSearch
{
	// Normalize both queries and labels, so abbreviations and their full names work in either direction.
	private static readonly Dictionary<string, string> Aliases = new( StringComparer.Ordinal )
	{
		["fov"] = "field of view",
		["ads"] = "aim down sights",
		["pip"] = "picture in picture",
		["ptt"] = "push to talk",
		["sfx"] = "sound effects",
		["ui"] = "user interface sounds",
		["gamepad"] = "controller",
		["sens"] = "sensitivity",
		["colour"] = "color",
		["theatre"] = "theater",
	};

	private static string Normalize( string text )
	{
		var folded = LanguageMenu.Fold( text ?? "" );
		var normalized = new System.Text.StringBuilder( folded.Length );
		foreach ( var c in folded )
		{
			// Preserve symbol keys such as + and = while treating word separators alike.
			normalized.Append( char.IsWhiteSpace( c ) || c is '-' or '_' or '‐' or '‑' or '–' or '—' ? ' ' : c );
		}

		return string.Join( ' ', normalized.ToString().Split( ' ', StringSplitOptions.RemoveEmptyEntries )
			.Select( word => Aliases.TryGetValue( word, out var alias ) ? alias : word ) );
	}

	public static string[] Words( string query ) => Normalize( query ).Split( ' ', StringSplitOptions.RemoveEmptyEntries );

	/// <summary>Whether every word is in one of the texts. No words matches nothing.</summary>
	public static bool Matches( string[] words, params string[] texts )
	{
		if ( words is null || words.Length == 0 )
			return false;

		var haystack = Normalize( string.Join( ' ', texts.Where( x => !string.IsNullOrEmpty( x ) ) ) );
		return words.All( word => haystack.Contains( word, StringComparison.Ordinal ) );
	}

	/// <summary>Whether a setting matches: its title and category, translated and in English.</summary>
	public static bool Matches( string[] words, PropertyDescription setting ) =>
		Matches( words, setting.Title, GameText.Get( setting.Title ), setting.Group, GameText.Get( setting.Group ) );
}
