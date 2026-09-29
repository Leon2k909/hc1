namespace Facepunch;

/// <summary>
/// The game's own text language (Settings → Game → Language), separate from the player's s&amp;box language. Code writes
/// its text in English and shows it through <c>Tr( "..." )</c> (<see cref="GlobalGameNamespace"/>), which looks that
/// English up in the language's table, so anything without a translation still reads in English. The tables are in
/// Code/Settings/Text: English → French, German, Spanish and Brazilian Portuguese. The languages after those (Italian
/// onwards) have a table each in Code/Settings/Text/Languages, with the same English keys.
/// </summary>
public static partial class GameText
{
	/// <summary> English text → its (French, German, Spanish, Brazilian Portuguese). Keys ignore case. </summary>
	private sealed class TextTable : Dictionary<string, (string Fr, string De, string Es, string Pt)>
	{
		public TextTable() : base( StringComparer.OrdinalIgnoreCase ) { }
	}

	/// <summary> English text → one language's text, for a language with a table of its own. Keys ignore case. </summary>
	private sealed class LanguageTable : Dictionary<string, string>
	{
		public LanguageTable() : base( StringComparer.OrdinalIgnoreCase ) { }
	}

	/// <summary> The language's own table (Code/Settings/Text/Languages), or null if it's English or in the tables' columns. </summary>
	private static LanguageTable OwnTable( GameLanguage language ) => language switch
	{
		GameLanguage.Italian => ItalianText,
		GameLanguage.Polish => PolishText,
		GameLanguage.Russian => RussianText,
		GameLanguage.Ukrainian => UkrainianText,
		GameLanguage.Turkish => TurkishText,
		GameLanguage.Japanese => JapaneseText,
		GameLanguage.Korean => KoreanText,
		GameLanguage.ChineseSimplified => ChineseSimplifiedText,
		GameLanguage.ChineseTraditional => ChineseTraditionalText,
		_ => null
	};

	/// <summary>
	/// Every table. The shared words come last, so they win over a page's own copy and every page says them the same
	/// way. The tables are properties that build a new table each time, so a hotload picks up edited text.
	/// </summary>
	private static TextTable[] Tables => new[] { MenuText, PageText, OperatorsText, SettingsText, GunsmithText, MatchText, HudText, CommonText };

	public static GameLanguage Current => GameSettingsSystem.Current.Language is var language
		&& language >= GameLanguage.EnglishUK && language <= GameLanguage.ChineseTraditional ? language : GameLanguage.EnglishUK;

	public static bool IsEnglish => Current is GameLanguage.EnglishUK or GameLanguage.EnglishUS;

	/// <summary> A language's name in that language, for the picker. </summary>
	public static string NativeName( GameLanguage language ) => language switch
	{
		GameLanguage.EnglishUS => "English (US)",
		GameLanguage.French => "Français",
		GameLanguage.German => "Deutsch",
		GameLanguage.Spanish => "Español",
		GameLanguage.PortugueseBrazil => "Português (Brasil)",
		GameLanguage.Italian => "Italiano",
		GameLanguage.Polish => "Polski",
		GameLanguage.Russian => "Русский",
		GameLanguage.Ukrainian => "Українська",
		GameLanguage.Turkish => "Türkçe",
		GameLanguage.Japanese => "日本語",
		GameLanguage.Korean => "한국어",
		GameLanguage.ChineseSimplified => "简体中文",
		GameLanguage.ChineseTraditional => "繁體中文",
		_ => "English (UK)"
	};

	/// <summary> A language's name in English ("Japanese" for 日本語), so the picker can find it whatever it's showing. </summary>
	public static string EnglishName( GameLanguage language ) => language switch
	{
		GameLanguage.EnglishUS => "English (US)",
		GameLanguage.French => "French",
		GameLanguage.German => "German",
		GameLanguage.Spanish => "Spanish",
		GameLanguage.PortugueseBrazil => "Portuguese (Brazil)",
		GameLanguage.Italian => "Italian",
		GameLanguage.Polish => "Polish",
		GameLanguage.Russian => "Russian",
		GameLanguage.Ukrainian => "Ukrainian",
		GameLanguage.Turkish => "Turkish",
		GameLanguage.Japanese => "Japanese",
		GameLanguage.Korean => "Korean",
		GameLanguage.ChineseSimplified => "Chinese (Simplified)",
		GameLanguage.ChineseTraditional => "Chinese (Traditional)",
		_ => "English (UK)"
	};

	// Built on first use and again after a language change. [SkipHotload] leaves them null after a hotload, so edited
	// tables are read again.
	[SkipHotload] private static Dictionary<string, string> _shown;
	[SkipHotload] private static Dictionary<string, string> _translations;
	[SkipHotload] private static HashSet<string> _missing;
	[SkipHotload] private static GameLanguage _language;

	/// <summary> <paramref name="english"/> in the player's language: its translation, or the English if there's none. </summary>
	public static string Get( string english )
	{
		if ( string.IsNullOrEmpty( english ) ) return english ?? "";

		var language = Current;
		if ( _shown is null || _language != language ) Load( language );
		if ( !_shown.TryGetValue( english, out var shown ) )
			_shown[english] = shown = Translate( english, language );
		return shown;
	}

	/// <summary> <see cref="Get"/> of a format string ("{0} XP TO LEVEL {1}"), filled in with <paramref name="args"/>. </summary>
	public static string Format( string english, params object[] args )
	{
		try { return string.Format( Get( english ), args ); }
		catch ( FormatException )
		{
			// A translation with a broken placeholder shows the English instead, and broken English shows as written.
			try { return string.Format( english, args ); }
			catch ( FormatException ) { return english; }
		}
	}

	/// <summary> Switches the game's language, saves it, and redraws every panel so what's on screen changes at once. </summary>
	public static void SetLanguage( GameLanguage language )
	{
		GameSettingsSystem.Current.Language = language;
		GameSettingsSystem.Save();
		_shown = null;
		Refresh();
	}

	/// <summary> The text shown in English this session because the language's table doesn't have it. </summary>
	public static IEnumerable<string> Missing => _missing ?? Enumerable.Empty<string>();

	private static void Load( GameLanguage language )
	{
		_language = language;
		_shown = new();
		_missing = new( StringComparer.OrdinalIgnoreCase );
		_translations = new( StringComparer.OrdinalIgnoreCase );
		if ( language is GameLanguage.EnglishUK or GameLanguage.EnglishUS ) return;

		foreach ( var (english, translated) in Entries( language ) )
		{
			if ( string.IsNullOrWhiteSpace( translated ) ) continue;

			// The code's English spells a word either way ("Armor", "Armour"), so each key matches both.
			_translations[english] = translated;
			_translations.TryAdd( Respell( english, british: true ), translated );
			_translations.TryAdd( Respell( english, british: false ), translated );
		}
	}

	/// <summary> Each English text with its <paramref name="language"/> text: from its own table, or its tables' column. </summary>
	private static IEnumerable<(string English, string Text)> Entries( GameLanguage language )
	{
		if ( OwnTable( language ) is { } own )
		{
			foreach ( var (english, text) in own )
				yield return (english, text);
			yield break;
		}

		foreach ( var table in Tables )
		{
			foreach ( var (english, text) in table )
			{
				yield return (english, language switch
				{
					GameLanguage.French => text.Fr,
					GameLanguage.German => text.De,
					GameLanguage.Spanish => text.Es,
					_ => text.Pt
				});
			}
		}
	}

	private static string Translate( string english, GameLanguage language )
	{
		if ( language is GameLanguage.EnglishUK or GameLanguage.EnglishUS )
			return Respell( english, language == GameLanguage.EnglishUK );

		if ( !_translations.TryGetValue( english, out var text ) )
		{
			_missing.Add( english );
			return english;
		}

		// Text written in capitals ("PLAY NOW") shows its translation in capitals too.
		return IsCapitals( english ) ? Capitalise( text, language ) : text;
	}

	/// <summary> Whether the text's letters are all capitals, not counting format placeholders ("{0:mm\\:ss}"). </summary>
	private static bool IsCapitals( string text )
	{
		var letters = false;
		var depth = 0;
		foreach ( var c in text )
		{
			if ( c == '{' ) depth++;
			else if ( c == '}' && depth > 0 ) depth--;
			else if ( depth == 0 && char.IsLetter( c ) )
			{
				if ( char.IsLower( c ) ) return false;
				letters = true;
			}
		}
		return letters;
	}

	/// <summary>
	/// The text in capitals, leaving format placeholders alone ("mm" is minutes, "MM" months). A capital ß is rare in
	/// German type, so capitals spell it SS. Turkish keeps the dot on a capital i (İ), since its I is a different letter:
	/// the capital of the dotless ı, which the invariant casing leaves in lower case ("ATıŞ HıZı").
	/// </summary>
	private static string Capitalise( string text, GameLanguage language )
	{
		var result = new System.Text.StringBuilder( text.Length + 4 );
		var depth = 0;
		foreach ( var c in text )
		{
			if ( c == '{' ) depth++;
			else if ( c == '}' && depth > 0 ) { depth--; result.Append( c ); continue; }

			if ( depth > 0 ) result.Append( c );
			else if ( c == 'ß' ) result.Append( "SS" );
			else if ( c == 'i' && language == GameLanguage.Turkish ) result.Append( 'İ' );
			else if ( c == 'ı' ) result.Append( 'I' );
			else result.Append( char.ToUpperInvariant( c ) );
		}
		return result.ToString();
	}

	/// <summary> British and American spellings of the words the game uses, since its English mixes the two. </summary>
	private static (string British, string American)[] Spellings => new[]
	{
		("colour", "color"), ("colours", "colors"), ("centre", "center"), ("centred", "centered"),
		("customise", "customize"), ("customised", "customized"), ("customisation", "customization"),
		("armour", "armor"), ("armoured", "armored"), ("favourite", "favorite"), ("favourites", "favorites"),
		("grey", "gray"), ("defence", "defense"), ("honour", "honor"), ("behaviour", "behavior"),
		("personalise", "personalize"), ("optimise", "optimize"), ("organise", "organize"), ("recognise", "recognize"),
		("metre", "meter"), ("metres", "meters"), ("cancelled", "canceled"), ("travelled", "traveled"),
		("catalogue", "catalog"), ("analyse", "analyze"), ("minimise", "minimize"), ("maximise", "maximize"),
	};

	/// <summary> <paramref name="text"/> with each word in British or American spelling, keeping its capitals. </summary>
	private static string Respell( string text, bool british )
	{
		var result = new System.Text.StringBuilder( text.Length );
		var i = 0;
		while ( i < text.Length )
		{
			if ( !char.IsLetter( text[i] ) ) { result.Append( text[i++] ); continue; }

			var start = i;
			while ( i < text.Length && char.IsLetter( text[i] ) ) i++;
			var word = text.Substring( start, i - start );
			var lower = word.ToLowerInvariant();

			string swapped = null;
			foreach ( var (b, a) in Spellings )
			{
				if ( british && lower == a ) { swapped = b; break; }
				if ( !british && lower == b ) { swapped = a; break; }
			}

			if ( swapped is null ) result.Append( word );
			else if ( IsCapitals( word ) && word.Length > 1 ) result.Append( swapped.ToUpperInvariant() );
			else if ( char.IsUpper( word[0] ) ) result.Append( char.ToUpperInvariant( swapped[0] ) ).Append( swapped, 1, swapped.Length - 1 );
			else result.Append( swapped );
		}
		return result.ToString();
	}

	/// <summary>
	/// Redraws every panel, so text already on screen changes language. A panel otherwise only redraws when its own
	/// BuildHash changes, which a language change doesn't touch.
	/// </summary>
	private static void Refresh()
	{
		var scene = Game.ActiveScene;
		if ( scene is null ) return;

		foreach ( var component in scene.GetAllComponents<PanelComponent>() )
		{
			component.StateHasChanged();
			if ( component.Panel is null ) continue;
			foreach ( var panel in component.Panel.Descendants )
				panel.StateHasChanged();
		}
	}
}
