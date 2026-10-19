using Sandbox.UI;

namespace Facepunch.UI;

/// <summary>
/// A menu, popup or dialog the pad drives (<see cref="PadNavigation"/>). It offers itself every Tick while it's up,
/// with <see cref="PadNavigation.Offer"/>.
/// </summary>
public interface IPadScope
{
	/// <summary>Where focus lands when the D-pad first takes over here: a target, or a panel to take the first target in.
	/// Null for the target under the pointer, else the scope's first.</summary>
	Panel PadFirstFocus { get; }

	/// <summary>B: back out of this UI. False leaves B to the game, as Escape.</summary>
	bool PadBack();

	/// <summary>LT and RT (-1 and 1): the UI's own tabs, like the settings' categories. False if it has none.</summary>
	bool PadTab( int direction );
}

/// <summary>
/// An <see cref="IPadScope"/> made of delegates, for a UI that offers more than one scope (a page and the popups it
/// opens). Keep it in a field: <see cref="PadNavigation.Offer"/> is called every Tick.
/// </summary>
public sealed class PadScope : IPadScope
{
	public Func<Panel> First { get; init; }
	public Func<bool> Back { get; init; }
	public Func<int, bool> Tab { get; init; }

	public Panel PadFirstFocus => First?.Invoke();
	public bool PadBack() => Back?.Invoke() ?? false;
	public bool PadTab( int direction ) => Tab?.Invoke( direction ) ?? false;
}

/// <summary>A pad target that left and right change rather than leave: a settings row, a slider.</summary>
public interface IPadAdjustable
{
	/// <summary>One step each way. <paramref name="heldFor"/> is how long the D-pad has been held, to speed up a long
	/// slider. False if this target has nothing to change, and left or right moves off it.</summary>
	bool PadAdjust( int direction, float heldFor );

	/// <summary>Where the pointer rests, so A presses the right part: a checkbox, the chosen option, a slider's thumb.
	/// Null for the middle of the target.</summary>
	Panel PadPoint { get; }
}

/// <summary>
/// Drives menus with a controller. s&amp;box's virtual cursor already lets the left stick move the pointer, A click
/// and the right stick scroll. This adds the D-pad: it moves a focus from control to control, the nearest one that
/// way, and the pointer follows it, so A presses whatever has the focus (and hover styles and sounds work as for a
/// mouse). Left and right change a focused setting instead of leaving it (<see cref="IPadAdjustable"/>, sliders).
/// B backs out, and LT and RT change tabs (<see cref="IPadScope"/>).
/// <para>Only a UI that offers itself is driven, the topmost layer when several are up (a dialog over the settings).
/// Scopes on one layer that sit inside each other are driven as one, the outermost's panel: the main menu offers itself
/// and so does its page, so the D-pad reaches the header from the page. B, LT and RT and the first focus ask the
/// innermost first. While a UI is driven, the pad buttons it uses are taken from the game: in the pause menu the D-pad
/// would otherwise drop the gun (Drop) or open the class menu (ChooseClass).</para>
/// <para>Targets are a scope's panels with the <see cref="TargetClass"/> class, checkboxes and sliders, or a pointer
/// cursor (a button); not what's inside one. <see cref="SkipClass"/> leaves a panel and what's in it out. The focused
/// one gets <see cref="FocusClass"/>. The first focus is a <see cref="FirstClass"/> target, else the first that isn't
/// in a <see cref="LateClass"/> panel (a page's back button). Moving the stick or the mouse hands the pointer back.</para>
/// </summary>
public sealed class PadNavigation : GameObjectSystem<PadNavigation>
{
	// Menu actions (ProjectSettings/Input.config, group "Menus", hidden from the keybinds): the pad only.
	public const string Up = "MenuUp", Down = "MenuDown", Left = "MenuLeft", Right = "MenuRight";
	public const string Select = "MenuSelect", Back = "MenuBack", PrevTab = "MenuPrevTab", NextTab = "MenuNextTab";

	public const string TargetClass = "pad-target", SkipClass = "pad-skip", FocusClass = "pad-focus";
	public const string FirstClass = "pad-first", LateClass = "pad-late";

	/// <summary>A held direction repeats after this long...</summary>
	const float RepeatDelay = 0.35f;

	/// <summary>...this often when it moves the focus...</summary>
	const float MoveEvery = 0.09f;

	/// <summary>...and this often when it changes a value.</summary>
	const float AdjustEvery = 0.06f;

	/// <summary>The pad buttons a driven UI takes from the game.</summary>
	static readonly GamepadCode[] MenuButtons =
	{
		GamepadCode.DpadNorth, GamepadCode.DpadSouth, GamepadCode.DpadWest, GamepadCode.DpadEast,
		GamepadCode.A, GamepadCode.B, GamepadCode.LeftTrigger, GamepadCode.RightTrigger,
	};

	sealed class Offered
	{
		public Panel Panel;
		public IPadScope Handler;
		public int Layer;
		public int Order;
		public RealTimeSince Seen;

		/// <summary>The focus it had when a popup or dialog went over it, to go back to.</summary>
		public Panel LastFocus;
	}

	sealed class Held
	{
		public bool Down;
		public RealTimeSince Since;
		public float Next;
	}

	static readonly List<Offered> Scopes = new();
	static readonly Dictionary<string, Held> HeldButtons = new();
	static int _order;

	/// <summary>The driven scope: the innermost of <see cref="Chain"/>.</summary>
	static Offered _scope;

	/// <summary>The driven scopes, innermost first: the scope and those on its layer it sits inside.</summary>
	static readonly List<Offered> Chain = new();

	/// <summary>The outermost scope's panel: where the targets are.</summary>
	static Panel _area;

	static string[] _consumed;

	/// <summary>True once the D-pad has the focus, until the stick or the mouse moves the pointer.</summary>
	static bool _driving;

	/// <summary>Frames to wait before picking a new focus, for a tab's page to be drawn.</summary>
	static int _settle;

	/// <summary>Where the focus last was, while it was there to use.</summary>
	static Rect _focusRect;

	/// <summary>Where the focus was when it went away (a press swapped the list it was in), until a new one is picked.</summary>
	static Rect? _lostAt;

	static Vector2 _point;
	static int _pointFrames;

	/// <summary>The panel the D-pad has focused, while it's driving.</summary>
	public static Panel Focus { get; private set; }

	/// <summary>Whether the D-pad is driving a UI (for button hints).</summary>
	public static bool IsDriving => _driving && Focus.IsValid();

	/// <summary>Whether a UI is being offered to the pad right now.</summary>
	public static bool HasScope => _scope is not null;

	/// <summary>
	/// Offer a UI to the pad, every Tick while it's up. <paramref name="layer"/> puts a popup or a dialog over the page
	/// under it; among equals, the one offered first is under.
	/// </summary>
	public static void Offer( Panel scope, IPadScope handler, int layer = 0 )
	{
		if ( !scope.IsValid() ) return;

		foreach ( var offered in Scopes )
		{
			if ( offered.Panel != scope ) continue;
			offered.Handler = handler;
			offered.Layer = layer;
			offered.Seen = 0;
			return;
		}

		Scopes.Add( new Offered { Panel = scope, Handler = handler, Layer = layer, Order = ++_order, Seen = 0 } );
	}

	public PadNavigation( Scene scene ) : base( scene )
	{
		// Before the game's components, so the buttons a menu uses can be taken from them.
		Listen( Stage.StartUpdate, -100, Update, "PadNavigation" );
	}

	private void Update()
	{
		if ( Scene.IsEditor || Scene != Game.ActiveScene )
			return;

		Scopes.RemoveAll( x => !x.Panel.IsValid() || x.Panel.IsDeleting || x.Seen > 0.25f );
		var scope = PickScope();
		var area = Chain.Count > 0 ? Chain[^1].Panel : null;

		if ( scope != _scope || area != _area )
		{
			if ( _scope is not null ) _scope.LastFocus = Focus;
			_scope = scope;
			_area = area;
			_consumed = null;
			_lostAt = null;

			// Back from a popup or a dialog, the focus goes back where it was.
			var last = scope?.LastFocus;
			SetFocus( _driving && Usable( last, area ) ? last : null );
		}

		if ( scope is null || !Input.UsingController )
		{
			Stop();
			HeldButtons.Clear();
			return;
		}

		var up = Repeat( Up, MoveEvery, out var heldFor );
		var down = Repeat( Down, MoveEvery, out var heldDown );
		var left = Repeat( Left, AdjustEvery, out var heldLeft );
		var right = Repeat( Right, AdjustEvery, out var heldRight );
		var back = Repeat( Back, float.MaxValue, out _ );
		var prevTab = Repeat( PrevTab, float.MaxValue, out _ );
		var nextTab = Repeat( NextTab, float.MaxValue, out _ );
		Consume();

		// The stick or the mouse moved the pointer: it's theirs again.
		if ( _driving && (StickMoved() || PointerMoved()) )
			Stop();

		if ( back && !Chain.Any( x => x.Handler?.PadBack() == true ) )
			Input.EscapePressed = true;

		var tab = nextTab ? 1 : -1;
		if ( (prevTab || nextTab) && Chain.Any( x => x.Handler?.PadTab( tab ) == true ) && _driving )
		{
			SetFocus( null );
			_settle = 2;
		}

		if ( up ) Step( new Vector2( 0, -1 ), heldFor );
		else if ( down ) Step( new Vector2( 0, 1 ), heldDown );
		else if ( left ) Step( new Vector2( -1, 0 ), heldLeft );
		else if ( right ) Step( new Vector2( 1, 0 ), heldRight );

		if ( !_driving ) return;

		if ( _settle > 0 )
		{
			_settle--;
			return;
		}

		if ( !Usable( Focus, _area ) )
		{
			// The focused control went away: A swapped the list it was in (a gunsmith slot for its parts). Wait for the
			// new list to be laid out, then take the control nearest where it was, not the page's first.
			if ( Focus is not null && _lostAt is null )
			{
				_lostAt = _focusRect;
				SetFocus( null );
				_settle = 2;
				return;
			}

			SetFocus( (_lostAt is { } lost ? Replacement( lost ) : null) ?? FirstFocus() );
		}

		if ( Focus.IsValid() ) _focusRect = Focus.Box.Rect;
		PointAtFocus();
	}

	/// <summary>
	/// The focus for one that went away from <paramref name="lost"/>: the target nearest it, or the list that one is in
	/// picks its own (a <see cref="FirstClass"/> target, like the fitted part).
	/// </summary>
	private static Panel Replacement( Rect lost )
	{
		var targets = Targets( _area );
		if ( targets.Count == 0 ) return null;

		var nearest = targets.OrderBy( x => PadNavMath.Distance( x.Box.Rect, lost ) ).First();

		// The list it's in: the nearest panel round it with other targets.
		for ( var list = nearest.Parent; list.IsValid() && list != _area; list = list.Parent )
		{
			var inList = Targets( list );
			if ( inList.Count < 2 ) continue;
			return inList.FirstOrDefault( x => x.HasClass( FirstClass ) ) ?? nearest;
		}

		return nearest;
	}

	/// <summary>
	/// The scope to drive, and <see cref="Chain"/>: on the top layer of those shown, the one inside the most others,
	/// then the latest, with the ones it's inside.
	/// </summary>
	private static Offered PickScope()
	{
		Chain.Clear();

		var top = int.MinValue;
		foreach ( var x in Scopes )
			if ( x.Panel.IsVisible && x.Layer > top ) top = x.Layer;

		Offered primary = null;
		var primaryDepth = -1;
		foreach ( var x in Scopes )
		{
			if ( x.Layer != top || !x.Panel.IsVisible ) continue;

			var depth = Scopes.Count( o => o != x && o.Layer == top && o.Panel.IsVisible && x.Panel.IsAncestor( o.Panel ) );
			if ( depth > primaryDepth || (depth == primaryDepth && x.Order > primary.Order) )
			{
				primary = x;
				primaryDepth = depth;
			}
		}

		if ( primary is null ) return null;

		Chain.Add( primary );
		foreach ( var o in Scopes )
		{
			if ( o != primary && o.Layer == top && o.Panel.IsVisible && primary.Panel.IsAncestor( o.Panel ) )
				Chain.Add( o );
		}

		// Innermost first: the deeper a scope's panel, the further in it is.
		Chain.Sort( ( a, b ) => b.Panel.Ancestors.Count().CompareTo( a.Panel.Ancestors.Count() ) );
		return primary;
	}

	/// <summary>A D-pad press: the first takes the focus, the rest move it or change what has it.</summary>
	private static void Step( Vector2 direction, float heldFor )
	{
		if ( !_driving || !Usable( Focus, _area ) )
		{
			_driving = true;
			_settle = 0;
			SetFocus( Hovered( _area ) ?? FirstFocus() );
			return;
		}

		if ( direction.y == 0 && Adjust( Focus, (int)direction.x, heldFor ) )
			return;

		var targets = Targets( _area );
		var rects = targets.Select( x => x.Box.Rect ).ToList();
		var next = PadNavMath.Pick( Focus.Box.Rect, rects, direction, targets.IndexOf( Focus ) );
		if ( next >= 0 ) SetFocus( targets[next] );
	}

	private static bool Adjust( Panel target, int direction, float heldFor )
	{
		if ( target is IPadAdjustable adjustable )
			return adjustable.PadAdjust( direction, heldFor );

		if ( target is CustomSlider slider )
		{
			slider.Value = PadNavMath.SliderStep( slider.Value, slider.Min, slider.Max, slider.Step, direction, heldFor );
			slider.OnValueChanged?.Invoke( slider.Value );
			return true;
		}

		if ( target is SliderControl engineSlider )
		{
			engineSlider.Value = PadNavMath.SliderStep( engineSlider.Value, engineSlider.Min, engineSlider.Max, engineSlider.Step, direction, heldFor );
			engineSlider.OnValueChanged?.Invoke( engineSlider.Value );
			return true;
		}

		return false;
	}

	/// <summary>Every target in a scope, in the order they're drawn.</summary>
	public static List<Panel> Targets( Panel scope )
	{
		var list = new List<Panel>();
		Collect( scope, list );
		return list;
	}

	private static void Collect( Panel panel, List<Panel> into )
	{
		foreach ( var child in panel.Children )
		{
			if ( !child.IsValid() || !child.IsVisible || child.HasClass( SkipClass ) )
				continue;

			if ( IsTarget( child ) )
			{
				var rect = child.Box.Rect;
				if ( rect.Width > 2f && rect.Height > 2f ) into.Add( child );
				CollectMarked( child, into );
				continue;
			}

			Collect( child, into );
		}
	}

	/// <summary>
	/// The <see cref="TargetClass"/> controls inside a target, like a row's TUNE button. Only marked ones: a pointer cursor
	/// is inherited, so everything in a button has one.
	/// </summary>
	private static void CollectMarked( Panel panel, List<Panel> into )
	{
		foreach ( var child in panel.Children )
		{
			if ( !child.IsValid() || !child.IsVisible || child.HasClass( SkipClass ) )
				continue;

			if ( child.HasClass( TargetClass ) )
			{
				var rect = child.Box.Rect;
				if ( rect.Width > 2f && rect.Height > 2f ) into.Add( child );
			}

			CollectMarked( child, into );
		}
	}

	/// <summary>
	/// A text box is a target so A can focus it, for a keyboard or the Steam on-screen keyboard (a class's or build's
	/// name, an import code, a bug report's title). It's never the first focus (<see cref="FirstIn"/>).
	/// </summary>
	private static bool IsTarget( Panel panel ) =>
		panel.HasClass( TargetClass ) || panel is Checkbox || panel is CustomSlider || panel is SliderControl || panel is TextEntry
		|| panel.ComputedStyle?.Cursor == "pointer";

	/// <summary>Whether the focus is still there to use: alive, shown and in the scope.</summary>
	private static bool Usable( Panel panel, Panel scope ) =>
		panel.IsValid() && scope.IsValid() && !panel.IsDeleting && panel.IsVisible && (panel == scope || panel.IsAncestor( scope ));

	/// <summary>Where the focus starts: the innermost scope's pick that's shown, else the area's first target.</summary>
	private static Panel FirstFocus()
	{
		foreach ( var offered in Chain )
		{
			var preferred = offered.Handler?.PadFirstFocus;
			if ( !Usable( preferred, _area ) ) continue;
			if ( IsTarget( preferred ) ) return preferred;

			var inside = FirstIn( preferred );
			if ( inside.IsValid() ) return inside;
		}

		return _area.IsValid() ? FirstIn( _area ) : null;
	}

	/// <summary>
	/// A panel's first target: one marked <see cref="FirstClass"/>, else the first that isn't a text box or in a
	/// <see cref="LateClass"/> panel.
	/// </summary>
	private static Panel FirstIn( Panel panel )
	{
		var targets = Targets( panel );
		return targets.FirstOrDefault( x => x.HasClass( FirstClass ) )
			?? targets.FirstOrDefault( x => x is not TextEntry && !x.AncestorsAndSelf.Any( a => a.HasClass( LateClass ) ) )
			?? targets.FirstOrDefault();
	}

	/// <summary>The target under the pointer, so the D-pad takes over where the stick left off.</summary>
	private static Panel Hovered( Panel scope )
	{
		var mouse = Mouse.Position;
		return Targets( scope ).Where( x => x.Box.Rect.IsInside( mouse ) )
			.OrderBy( x => x.Box.Rect.Width * x.Box.Rect.Height ).FirstOrDefault();
	}

	private static void SetFocus( Panel panel )
	{
		if ( Focus == panel ) return;

		if ( Focus.IsValid() ) Focus.SetClass( FocusClass, false );
		Focus = panel;
		_pointFrames = 0;

		if ( !panel.IsValid() ) return;
		_lostAt = null;
		panel.SetClass( FocusClass, true );
		ScrollIntoView( panel );
	}

	/// <summary>Scrolls every list it's in the least that shows it, the innermost first.</summary>
	private static void ScrollIntoView( Panel panel )
	{
		foreach ( var ancestor in panel.Ancestors )
		{
			if ( ancestor.ComputedStyle?.OverflowY == OverflowMode.Scroll || ancestor.ComputedStyle?.OverflowX == OverflowMode.Scroll )
				ancestor.ScrollIntoView( panel.Box.Rect );
		}
	}

	private static void Stop()
	{
		_driving = false;
		_settle = 0;
		SetFocus( null );
	}

	/// <summary>Keeps the pointer on the focus (it moves when a slider changes or the list scrolls), so A presses it.</summary>
	private static void PointAtFocus()
	{
		if ( !Focus.IsValid() ) return;

		var anchor = Focus;
		if ( Focus is IPadAdjustable adjustable && adjustable.PadPoint is { } point && point.IsValid() && point.IsVisible )
			anchor = point;
		else if ( Focus is CustomSlider or SliderControl && Focus.Descendants.FirstOrDefault( x => x.HasClass( "thumb" ) ) is { } thumb )
			anchor = thumb;

		var at = anchor.Box.Rect.Center;
		at = new Vector2( MathF.Floor( at.x ), MathF.Floor( at.y ) );

		_pointFrames = at.Distance( _point ) < 0.5f ? _pointFrames + 1 : 0;
		_point = at;
		Mouse.Position = at;
	}

	/// <summary>
	/// Whether the pointer left where the focus keeps it: the mouse moved it. Only once it has sat still a few frames,
	/// since moving it may only show a frame later.
	/// </summary>
	private static bool PointerMoved() => _pointFrames >= 3 && Mouse.Position.Distance( _point ) > 3f;

	private static bool StickMoved() =>
		MathF.Abs( Input.GetAnalog( InputAnalog.LeftStickX ) ) > 0.3f || MathF.Abs( Input.GetAnalog( InputAnalog.LeftStickY ) ) > 0.3f;

	/// <summary>
	/// Whether a menu action fires this frame: when first pressed, then every <paramref name="every"/> seconds once it's
	/// been held <see cref="RepeatDelay"/>. <paramref name="heldFor"/> is how long it's been held.
	/// </summary>
	private static bool Repeat( string action, float every, out float heldFor )
	{
		heldFor = 0f;
		if ( !HeldButtons.TryGetValue( action, out var held ) )
			HeldButtons[action] = held = new Held();

		if ( !Input.Down( action, false ) )
		{
			held.Down = false;
			return false;
		}

		if ( !held.Down )
		{
			held.Down = true;
			held.Since = 0;
			held.Next = RepeatDelay;
			return true;
		}

		heldFor = held.Since;
		if ( heldFor < held.Next ) return false;

		held.Next += every;
		return true;
	}

	/// <summary>Takes the menu's buttons from the game this frame: every action on them, the game's and the menu's.</summary>
	private static void Consume()
	{
		_consumed ??= Input.GetActions()
			.Where( x => !string.IsNullOrEmpty( x.Name ) && MenuButtons.Contains( x.GamepadCode ) )
			.Select( x => x.Name )
			.Distinct()
			.ToArray();

		foreach ( var action in _consumed )
			Input.Clear( action );
	}
}
