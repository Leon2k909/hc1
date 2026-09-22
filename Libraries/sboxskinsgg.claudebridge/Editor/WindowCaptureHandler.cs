using Sandbox;
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading.Tasks;

/// <summary>
/// screenshot_game — captures the editor window exactly as it is composited on screen (every camera,
/// viewmodel cameras, HUD), via Win32 PrintWindow. Works while the window is unfocused or covered, so no
/// screen control is needed. take_screenshot / capture_view only render a single camera.
/// Optional: crop {x,y,w,h} in window client pixels.
/// </summary>
public class WindowCaptureHandler : IBridgeHandler
{
	delegate bool EnumWindowsProc( IntPtr hwnd, IntPtr lParam );
	[DllImport( "user32.dll" )] static extern bool EnumWindows( EnumWindowsProc callback, IntPtr lParam );
	[DllImport( "user32.dll" )] static extern uint GetWindowThreadProcessId( IntPtr hwnd, out uint pid );
	[DllImport( "user32.dll", CharSet = CharSet.Unicode )] static extern int GetWindowText( IntPtr hwnd, System.Text.StringBuilder text, int max );
	[DllImport( "user32.dll" )] static extern bool IsWindowVisible( IntPtr hwnd );

	/// <summary>The editor's main window (title "... s&amp;box editor"); MainWindowHandle can be a dialog/wizard.</summary>
	static IntPtr FindEditorWindow()
	{
		var pid = (uint)System.Diagnostics.Process.GetCurrentProcess().Id;
		var found = IntPtr.Zero;
		EnumWindows( ( h, _ ) =>
		{
			GetWindowThreadProcessId( h, out var owner );
			if ( owner != pid || !IsWindowVisible( h ) ) return true;
			var sb = new System.Text.StringBuilder( 256 );
			GetWindowText( h, sb, sb.Capacity );
			if ( !sb.ToString().Contains( "s&box editor" ) ) return true;
			found = h;
			return false;
		}, IntPtr.Zero );
		return found != IntPtr.Zero ? found : System.Diagnostics.Process.GetCurrentProcess().MainWindowHandle;
	}

	[DllImport( "user32.dll" )] static extern bool PrintWindow( IntPtr hwnd, IntPtr hdc, uint flags );
	[DllImport( "user32.dll" )] static extern bool GetClientRect( IntPtr hwnd, out RECT rect );
	[DllImport( "user32.dll" )] static extern IntPtr GetDC( IntPtr hwnd );
	[DllImport( "user32.dll" )] static extern int ReleaseDC( IntPtr hwnd, IntPtr hdc );
	[DllImport( "gdi32.dll" )] static extern IntPtr CreateCompatibleDC( IntPtr hdc );
	[DllImport( "gdi32.dll" )] static extern IntPtr CreateCompatibleBitmap( IntPtr hdc, int w, int h );
	[DllImport( "gdi32.dll" )] static extern IntPtr SelectObject( IntPtr hdc, IntPtr obj );
	[DllImport( "gdi32.dll" )] static extern bool DeleteObject( IntPtr obj );
	[DllImport( "gdi32.dll" )] static extern bool DeleteDC( IntPtr hdc );
	[DllImport( "gdi32.dll" )] static extern int GetDIBits( IntPtr hdc, IntPtr bmp, uint start, uint lines, byte[] bits, ref BITMAPINFOHEADER info, uint usage );

	[StructLayout( LayoutKind.Sequential )] struct RECT { public int Left, Top, Right, Bottom; }
	[StructLayout( LayoutKind.Sequential )]
	struct BITMAPINFOHEADER
	{
		public uint biSize; public int biWidth, biHeight; public ushort biPlanes, biBitCount;
		public uint biCompression, biSizeImage; public int biXPelsPerMeter, biYPelsPerMeter; public uint biClrUsed, biClrImportant;
	}

	const uint PW_CLIENTONLY = 0x1, PW_RENDERFULLCONTENT = 0x2;

	public Task<object> Execute( JsonElement p )
	{
		var hwnd = FindEditorWindow();
		if ( hwnd == IntPtr.Zero ) return Task.FromResult<object>( new { error = "No editor main window handle." } );

		GetClientRect( hwnd, out var rc );
		int w = rc.Right - rc.Left, h = rc.Bottom - rc.Top;
		if ( w <= 0 || h <= 0 ) return Task.FromResult<object>( new { error = "Editor window is minimised." } );

		var screenDc = GetDC( IntPtr.Zero );
		var memDc = CreateCompatibleDC( screenDc );
		var hbmp = CreateCompatibleBitmap( screenDc, w, h );
		var old = SelectObject( memDc, hbmp );
		byte[] bgra;
		try
		{
			if ( !PrintWindow( hwnd, memDc, PW_CLIENTONLY | PW_RENDERFULLCONTENT ) )
				return Task.FromResult<object>( new { error = "PrintWindow failed." } );

			var info = new BITMAPINFOHEADER { biSize = 40, biWidth = w, biHeight = -h, biPlanes = 1, biBitCount = 32 };
			bgra = new byte[w * h * 4];
			SelectObject( memDc, old );
			GetDIBits( memDc, hbmp, 0, (uint)h, bgra, ref info, 0 );
		}
		finally
		{
			DeleteObject( hbmp );
			DeleteDC( memDc );
			ReleaseDC( IntPtr.Zero, screenDc );
		}

		var colors = new Color[w * h];
		for ( int i = 0; i < colors.Length; i++ )
			colors[i] = new Color( bgra[i * 4 + 2] / 255f, bgra[i * 4 + 1] / 255f, bgra[i * 4] / 255f, 1f );

		var bmp = new Bitmap( w, h );
		bmp.SetPixels( colors );
		if ( p.ValueKind == JsonValueKind.Object && p.TryGetProperty( "crop", out var c ) )
			bmp = bmp.Crop( new Rect( c.GetProperty( "x" ).GetSingle(), c.GetProperty( "y" ).GetSingle(), c.GetProperty( "w" ).GetSingle(), c.GetProperty( "h" ).GetSingle() ) );

		var path = Path.Combine( Path.GetTempPath(), $"bridge_window_{DateTime.Now:HHmmss_fff}.png" );
		File.WriteAllBytes( path, bmp.ToPng() );
		return Task.FromResult<object>( new { captured = true, path, width = bmp.Width, height = bmp.Height } );
	}
}
