using Sandbox.UI;

namespace Facepunch.UI;

/// <summary>Breakpoints in panel units, after the ScreenPanel's resolution scaling.</summary>
internal static class ResponsiveLayout
{
	public static void Update( Panel panel )
	{
		if ( panel is null ) return;

		var size = panel.Box.Rect.Size * panel.ScaleFromScreen;
		if ( size.x <= 0 || size.y <= 0 ) return;

		panel.SetClass( "compact", size.x < 1600 );
		panel.SetClass( "narrow", size.x < 1200 );
		panel.SetClass( "portrait", size.x < 800 );
		panel.SetClass( "short", size.y < 800 );
	}
}
