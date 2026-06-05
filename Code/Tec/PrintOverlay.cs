namespace Tec;

public sealed class PrintOverlay : Component
{
	private static PrintOverlay Instance { get; set; }

	private const float Duration = 2.0f;
	private const int MaxLines = 10;
	private static readonly Color DefaultColor = Color.Green;
	
	private struct Line( string text, Color color )
	{
		public readonly string Text = text;
		public readonly Color Color = color;
		public readonly float ExpirationTime = Time.Now + Duration;
	}

	private readonly List<Line> _lines = [];

	protected override void OnAwake()
	{
		Instance = this;
	}

	protected override void OnUpdate()
	{
		float y = 20f;

		for ( int i = _lines.Count -1; i > -1; i-- )
		{
			var line = _lines[i];

			if ( Time.Now > line.ExpirationTime || i < _lines.Count - MaxLines )
			{
				_lines.RemoveAt( i );
				continue;
			}

			DebugOverlay.ScreenText(
				new Vector2( 20, y ),
				line.Text,
				14,
				TextFlag.Left,
				line.Color,
				0.1f
			);

			y += 20f;
		}
	}

	public static void Print( string text, Color? color = null )
	{
		if ( Instance == null )
		{
			Log.Warning("PrintOverlay missing in scene.");
			return;
		}

		Instance._lines.Add(
			new Line( text, color ?? DefaultColor )
		);
	}
}
