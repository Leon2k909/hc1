namespace Facepunch.UI;

/// <summary>
/// The language picker's list (<see cref="LanguagePicker"/>, Settings → Game → Language): a search box over every
/// language, each named in its own language with its English name beside it. It's a <see cref="Popup"/> in the root
/// panel, so the settings list's scroll doesn't clip it, and s&amp;box closes it on a press anywhere outside it. Up and
/// Down move through it and Enter picks; Escape closes it before anything under it (<see cref="CloseAny"/>).
/// </summary>
public partial class LanguageMenu : IPadScope
{
	/// <summary> The list that's open, if any. </summary>
	private static LanguageMenu Shown;

	/// <summary> Every language, in order of its own name. </summary>
	private static List<GameLanguage> AllLanguages => Enum.GetValues<GameLanguage>()
		.OrderBy( GameText.NativeName, StringComparer.OrdinalIgnoreCase ).ToList();

	// Accented letters and their plain ones, so a search for "francais" finds Français and "turkce" Türkçe.
	private const string Accented = "àáâãäåçèéêëìíîïıñòóôõöøùúûüýÿşğłńśźżćęą";
	private const string Plain = "aaaaaaceeeeiiiiinoooooouuuuyysglnszzcea";

	private LanguageSearchEntry Search { get; set; }
	private Panel RowList { get; set; }

	private string Query { get; set; } = "";
	private List<GameLanguage> Matches { get; set; } = AllLanguages;

	/// <summary> The row Enter picks: the one under the mouse, or moved to with Up and Down. </summary>
	private int Highlight { get; set; }

	/// <summary> The highlighted row is to be scrolled into view once it's laid out. </summary>
	private bool _scrollPending = true;

	/// <summary> Where the mouse was when the keys last moved the highlight, so rows scrolled under a still mouse don't take it. </summary>
	private Vector2? _keysMouse;

	/// <summary> Opens the list under the field, with the current language highlighted and the search box focused. </summary>
	public static LanguageMenu Open( Panel field )
	{
		Shown?.Delete();

		var menu = new LanguageMenu();
		menu.SetPositioning( field, PositionMode.BelowStretch, 4 );
		menu.CloseWhenParentIsHidden = true;
		menu.Highlight = Math.Max( 0, menu.Matches.IndexOf( GameText.Current ) );
		Shown = menu;
		return menu;
	}

	/// <summary>
	/// Closes the open list, if there is one. MainMenuRoot, MainHUD and the pause menu ask this first when they take Escape:
	/// the list's own Tick is too late to see Escape, which s&amp;box's pause menu (or the editor) takes before panels tick.
	/// </summary>
	public static bool CloseAny()
	{
		if ( !Shown.IsValid() || Shown.IsDeleting ) return false;

		Shown.Delete();
		return true;
	}

	/// <summary> Whether a language's English name says more than its own name does (not for the two Englishes). </summary>
	public static bool ShowsEnglishName( GameLanguage language ) => GameText.EnglishName( language ) != GameText.NativeName( language );

	protected override void OnAfterTreeRender( bool firstTime )
	{
		base.OnAfterTreeRender( firstTime );
		if ( firstTime ) Search?.Focus();
	}

	public override void Tick()
	{
		base.Tick();
		if ( IsDeleting ) return;

		// The field went out of sight: the pause menu closed, or the settings moved on.
		if ( !PopupSource.IsValid() || !PopupSource.IsVisible )
		{
			Delete();
			return;
		}

		if ( _scrollPending ) ScrollToHighlight();
		PadNavigation.Offer( this, this, 50 );
	}

	// The pad (PadNavigation): the D-pad moves the pointer down the rows, which moves the highlight, A picks, B closes.
	public Panel PadFirstFocus => RowList?.Children.FirstOrDefault( x => x.HasClass( "highlight" ) ) ?? RowList;

	public bool PadBack() => CloseAny();

	public bool PadTab( int direction ) => false;

	private void SetQuery( string text )
	{
		Query = text ?? "";
		var words = Fold( Query ).Split( ' ', StringSplitOptions.RemoveEmptyEntries );
		Matches = AllLanguages.Where( x => IsMatch( x, words ) ).ToList();
		Highlight = 0;
		_scrollPending = true;
		StateHasChanged();
	}

	/// <summary> Up and Down in the search box move the highlight, going round at either end. </summary>
	private void MoveHighlight( int step )
	{
		if ( Matches.Count == 0 ) return;

		_keysMouse = Mouse.Position;
		Highlight = (Highlight + step + Matches.Count) % Matches.Count;
		_scrollPending = true;
		StateHasChanged();
	}

	private void Hover( int index )
	{
		if ( _keysMouse is { } keysMouse && keysMouse == Mouse.Position ) return;
		_keysMouse = null;

		if ( Highlight == index ) return;
		Highlight = index;
		StateHasChanged();
	}

	/// <summary> Enter in the search box picks the highlighted language. </summary>
	private void Submit()
	{
		if ( Highlight >= 0 && Highlight < Matches.Count )
		{
			Pick( Matches[Highlight] );
			return;
		}

		// Nothing matches: Enter took the focus from the search box, so it gets it back to change the search.
		Search?.Focus();
	}

	private void Pick( GameLanguage language )
	{
		Sound.Play( "ui_button_press" );
		Delete();

		if ( language != GameText.Current )
			GameText.SetLanguage( language );
	}

	private void ScrollToHighlight()
	{
		if ( !RowList.IsValid() ) return;

		var row = RowList.Children.Where( x => x.HasClass( "lm-row" ) ).ElementAtOrDefault( Highlight );
		if ( row is null )
		{
			_scrollPending = false;
			return;
		}

		// A new row has no size until it's laid out.
		if ( row.Box.Rect.Height <= 0 ) return;

		RowList.ScrollIntoView( row.Box.Rect );
		_scrollPending = false;
	}

	/// <summary> Whether a language's own name or its English one has every word of the search in it. </summary>
	private static bool IsMatch( GameLanguage language, string[] words )
	{
		var names = Fold( $"{GameText.NativeName( language )} {GameText.EnglishName( language )}" );
		return words.All( word => names.Contains( word, StringComparison.Ordinal ) );
	}

	/// <summary> The text in lower case with its accents taken off. The settings page's search folds with it too. </summary>
	internal static string Fold( string text )
	{
		var folded = new System.Text.StringBuilder( text.Length );
		foreach ( var c in text.ToLowerInvariant() )
		{
			var i = Accented.IndexOf( c );
			folded.Append( i >= 0 ? Plain[i] : c );
		}
		return folded.ToString();
	}
}

/// <summary> The language list's search box. Up and Down move the list's highlight instead of the caret. </summary>
public class LanguageSearchEntry : TextEntry
{
	public Action<int> OnArrow { get; set; }

	public override void OnButtonTyped( ButtonEvent e )
	{
		if ( e.Button is "up" or "down" )
		{
			e.StopPropagation = true;
			OnArrow?.Invoke( e.Button == "up" ? -1 : 1 );
			return;
		}

		base.OnButtonTyped( e );
	}
}
