namespace Facepunch.UI;

/// <summary>
/// The settings page's search: a setting or keybind matches when every word of the search is in its name, in the
/// player's language or in English, or in its category's name. Case and accents don't count.
/// </summary>
public static class SettingsSearch
{
	public static string[] Words( string query ) =>
		LanguageMenu.Fold( query ?? "" ).Split( ' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries );

	/// <summary>Whether every word is in one of the texts. No words matches nothing.</summary>
	public static bool Matches( string[] words, params string[] texts )
	{
		if ( words is null || words.Length == 0 )
			return false;

		var haystack = LanguageMenu.Fold( string.Join( ' ', texts.Where( x => !string.IsNullOrEmpty( x ) ) ) );
		return words.All( word => haystack.Contains( word, StringComparison.Ordinal ) );
	}

	/// <summary>Whether a setting matches: its title and category, translated and in English.</summary>
	public static bool Matches( string[] words, PropertyDescription setting ) =>
		Matches( words, setting.Title, GameText.Get( setting.Title ), setting.Group, GameText.Get( setting.Group ) );
}
