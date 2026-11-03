namespace Facepunch.UI;

/// <summary>
/// One of <see cref="HsvColorPicker"/>'s hue, saturation and brightness bars: a gradient track with a thumb. The mouse
/// (or the virtual cursor) drags it, and on a controller the D-pad's left and right step it (<see cref="IPadAdjustable"/>).
/// </summary>
public sealed class HsvStrip : Panel, IPadAdjustable
{
	/// <summary> Where the thumb sits, 0 at the left to 1 at the right. </summary>
	public float Value { get; private set; }

	/// <summary> The D-pad's finest step, as a share of the bar (<see cref="PadNavMath.SliderStep"/>). </summary>
	public float Step { get; set; } = 0.01f;

	/// <summary> The thumb was moved: its new value, and whether that's final (a drag let go, a D-pad step), to save. </summary>
	public Action<float, bool> Changed { get; set; }

	readonly Panel _track;
	readonly Panel _thumb;
	bool _dragging;

	// What the styles last got, so they're only set when something changes.
	float _shownValue = -1f;
	string _shownGradient;
	Color? _shownThumb;

	public HsvStrip()
	{
		AddClass( PadNavigation.TargetClass );
		_track = Add.Panel( "track" );
		_thumb = Add.Panel( "thumb" );
	}

	/// <summary>
	/// Puts the thumb at <paramref name="value"/>, filled <paramref name="thumb"/>, on a track painted
	/// <paramref name="gradient"/> (a CSS background-image; null keeps the stylesheet's).
	/// </summary>
	public void Show( float value, string gradient, Color thumb )
	{
		Value = value.Clamp( 0f, 1f );

		if ( Value != _shownValue )
		{
			_thumb.Style.Left = Length.Percent( Value * 100f );
			_shownValue = Value;
		}

		if ( gradient is not null && gradient != _shownGradient )
		{
			_track.Style.Set( $"background-image: {gradient};" );
			_shownGradient = gradient;
		}

		if ( thumb != _shownThumb )
		{
			_thumb.Style.BackgroundColor = thumb;
			_shownThumb = thumb;
		}
	}

	/// <summary>
	/// The drag is this bar's own. Otherwise s&amp;box gives a press to the nearest scrolling panel up the tree (the
	/// settings' column), which scrolls with the mouse while the thumb moves.
	/// </summary>
	public override bool WantsDrag => true;

	protected override void OnMouseDown( MousePanelEvent e )
	{
		if ( e.MouseButton != MouseButtons.Left ) return;

		_dragging = true;
		Follow( false );
		e.StopPropagation();
	}

	protected override void OnMouseUp( MousePanelEvent e )
	{
		if ( e.MouseButton != MouseButtons.Left || !_dragging ) return;

		_dragging = false;
		Follow( true );
	}

	public override void Tick()
	{
		base.Tick();
		if ( !_dragging ) return;

		// Let go where the panel never heard it: it isn't :active any more.
		if ( !HasActive )
		{
			_dragging = false;
			Changed?.Invoke( Value, true );
			return;
		}

		Follow( false );
	}

	/// <summary> The thumb under the pointer. </summary>
	void Follow( bool done )
	{
		var rect = Box.Rect;
		if ( rect.Width <= 0f ) return;

		var value = ((Mouse.Position.x - rect.Left) / rect.Width).Clamp( 0f, 1f );
		if ( value == Value && !done ) return;

		Value = value;
		Changed?.Invoke( value, done );
	}

	public bool PadAdjust( int direction, float heldFor )
	{
		var value = PadNavMath.SliderStep( Value, 0f, 1f, Step, direction, heldFor );
		if ( value != Value )
		{
			Value = value;
			Changed?.Invoke( value, true );
		}

		// At either end it stays, as a slider does: up and down leave it.
		return true;
	}

	/// <summary> A presses the thumb, so it keeps the colour already there. </summary>
	public Panel PadPoint => _thumb;
}
