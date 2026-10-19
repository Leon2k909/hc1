namespace Facepunch.UI;

/// <summary>
/// A relatively simple color slider panel. thank you Alex for your instagib code from 2021
/// <para>On a controller, left and right turn the hue (<see cref="IPadAdjustable"/>), and the RGB boxes under it step
/// each channel (<see cref="ColorChannel"/>).</para>
/// </summary>
public partial class ColorSlider : IPadAdjustable
{
	public ColorSlider()
	{
		AddClass( PadNavigation.TargetClass );
	}
	public Image Image { get; set; }
	public Panel Cursor { get; set; }

	private bool IsDraggingMouse { get; set; }
	private byte[] ImageData;

	const int width = 360;
	const int height = width / 2;

	float Clamp( float a, bool isX = true )
	{
		return a.Clamp( 0, isX ? Image.Box.Rect.Size.x : Image.Box.Rect.Size.y - 1 );
	}

	Color GetColorAtPixel( int x, int y )
	{
		var index = (x + (y * width)) * 4;
		var range = 255f;

		// Just in case
		if ( index > ImageData.Count() )
			return Color.White;

		var col = new Color
		{
			r = ImageData[index] / range,
			g = ImageData[index + 1] / range,
			b = ImageData[index + 2] / range,
			a = ImageData[index + 3] / range
		};

		return col;
	}

	byte GetByte( float v ) 
	{
		return (byte)MathF.Floor( (v >= 1.0f) ? 255f : v * 256.0f );
	}

	private void CreateTexture()
	{
		var hsv = Color.Blue.ToHsv();

		var data = new byte[width * height * 4];
		ImageData = data;

		for ( int i = 0; i < data.Length; ++i )
			data[i] = byte.MaxValue;


		void SetPixel( int x, int y, Color col )
		{
			var index = (x + (y * width)) * 4;
			data[index] = GetByte( col.r );
			data[index + 1] = GetByte( col.g );
			data[index + 2] = GetByte( col.b );
			data[index + 3] = byte.MaxValue;
		}

		for ( int y = 0; y < height; y++ )
		{
			hsv.Hue = 0;

			for ( int x = 0; x < width; x++ )
			{
				var hsvConvert = hsv.ToColor();
				SetPixel( x, y, hsvConvert );
				hsv.Hue += 1;
			}

			// Random ass nubmer
			hsv.Saturation -= y * 0.000075f;
		}

		var texture = Texture.Create( width, height )
			.WithStaticUsage()
			.WithData( data )
			.Finish();

		Image.Texture = texture;
	}

	private void UpdateCursor()
	{
		Cursor.Style.Left = Clamp( MousePosition.x * ScaleFromScreen );
		Cursor.Style.Top = Clamp( MousePosition.y * ScaleFromScreen, false );
		// Not my proudest moment
		Cursor.Style.Set( $"background-image: radial-gradient( {Value.Hex}, {Value.Hex} 20%, black 75% );" );
	}

	public Color GetFromMouse()
	{
		var localPos = Mouse.Position - Image.Box.Rect.Position;

		localPos.x = Clamp( localPos.x );
		localPos.y = Clamp( localPos.y, false );

		var normalizedPos = localPos / Image.Box.Rect.Size;
		var arrayPos = normalizedPos * new Vector2( width, height );

		return GetColorAtPixel( (int)arrayPos.x, (int)arrayPos.y );
	}

	protected override void OnMouseDown( MousePanelEvent e )
	{
		if ( e.MouseButton == MouseButtons.Left )
			IsDraggingMouse = true;
	}

	protected override void OnMouseUp( MousePanelEvent e )
	{
		if ( e.MouseButton == MouseButtons.Left )
			IsDraggingMouse = false;
	}

	public override void Tick()
	{
		if ( IsDraggingMouse )
		{
			Value = GetFromMouse();
			UpdateCursor();
			_cursorShows = Value;
		}
		else if ( Value != _cursorShows && Image.IsValid() && Image.Box.Rect.Width > 0f )
		{
			// Set some other way (the pad, the RGB boxes, a saved colour): the cursor goes where that colour is.
			PlaceCursor();
		}
	}

	/// <summary> The colour the cursor was last put on. </summary>
	private Color? _cursorShows;

	/// <summary> The cursor on <see cref="Value"/>: its hue across the field, its saturation down it (CreateTexture's rows). </summary>
	private void PlaceCursor()
	{
		var hsv = Value.ToHsv();
		var x = hsv.Hue / 360f;
		// Row y's saturation is 1 less 0.000075 for each row above it, so about 1 - 0.0000375 y².
		var y = MathF.Min( MathF.Sqrt( MathF.Max( 0f, 1f - hsv.Saturation ) / 0.0000375f ), height - 1 ) / height;

		var image = Image.Box.Rect;
		Cursor.Style.Left = (image.Left - Box.Rect.Left + x * image.Width) * ScaleFromScreen;
		Cursor.Style.Top = (image.Top - Box.Rect.Top + y * image.Height) * ScaleFromScreen;
		Cursor.Style.Set( $"background-image: radial-gradient( {Value.Hex}, {Value.Hex} 20%, black 75% );" );
		_cursorShows = Value;
	}

	public bool PadAdjust( int direction, float heldFor )
	{
		var hsv = Value.ToHsv();

		// A grey or black has no hue to turn, so it starts from the field's full colour.
		if ( hsv.Saturation < 0.05f ) hsv.Saturation = 1f;
		if ( hsv.Value < 0.05f ) hsv.Value = 1f;

		var step = heldFor > 1.2f ? 12f : 3f;
		hsv.Hue = ((hsv.Hue + direction * step) % 360f + 360f) % 360f;
		Value = hsv.ToColor() with { a = Value.a };
		PlaceCursor();
		return true;
	}

	/// <summary> A presses the cursor, so it picks the colour already there. </summary>
	public Panel PadPoint => Cursor;

	protected override void OnAfterTreeRender( bool firstTime )
	{
		if ( firstTime )
		{
			CreateTexture();
		}
	}
}
