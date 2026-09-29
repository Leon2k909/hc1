using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using Editor;
using Sandbox;

/// <summary>
/// Real fullscreen play in the editor. The editor's own fullscreen (F3, or Full Screen On Play) only fills the editor
/// window, so its title/menu bar, the viewport toolbar, the status bar and the Windows taskbar stay on screen. This
/// hides those and stretches the editor window over the whole monitor. While playing, F3 (the editor's fullscreen
/// toggle) or F11 switches it on and off, and with Full Screen On Play ticked (Edit > Preferences) it comes on when
/// you press Play. Stopping (F5), ejecting (F8) or leaving the editor's fullscreen puts the editor back.
/// </summary>
public static class GameFullscreen
{
	public static bool IsActive { get; private set; }

	static bool _madeViewFullscreen;
	static bool _wasMaximized;
	static Vector2 _position, _size;
	static IntPtr _handle;
	static readonly List<Widget> _hidden = new();

	// The editor's fullscreen places the view under the title bar's height and above the status bar's (plus 4px), every
	// frame, even with them hidden. They're collapsed to nothing, and FitWindow grows the window past the monitor's
	// edges by whatever is left, so the view itself covers the monitor.
	static List<(Widget Widget, float MinimumHeight, float MaximumHeight)> _collapsed;
	static Rect _monitor;
	static int _fitAttempts, _fitWait;

	static bool _wasInGame;
	static bool _wasViewFullscreen;
	static int _enterInFrames = -1;

	static bool InGameView => SceneViewWidget.Current?.CurrentView == SceneViewWidget.ViewMode.Game;

	[Shortcut( "hc1.game-fullscreen", "F11", ShortcutType.Window )]
	static void Toggle()
	{
		if ( IsActive ) Exit();
		else Enter();
	}

	[EditorEvent.Frame]
	static void Frame()
	{
		var window = EditorWindow;
		var view = SceneViewWidget.Current;
		var inGame = InGameView;
		var viewFullscreen = window.IsValid() && view.IsValid() && window.IsFullscreen( view );

		// Play with Full Screen On Play, or F3 into the editor's fullscreen while playing. Wait a couple of frames so
		// the editor has laid the view out first.
		var pressedPlay = !_wasInGame && EditorPreferences.FullScreenOnPlay;
		var pressedF3 = viewFullscreen && !_wasViewFullscreen;
		if ( inGame && !IsActive && (pressedPlay || pressedF3) )
			_enterInFrames = 2;
		_wasInGame = inGame;
		_wasViewFullscreen = viewFullscreen;

		// Stopped, ejected, or F3 back out of the editor's fullscreen.
		if ( IsActive && (!inGame || !viewFullscreen) )
		{
			Exit();
			_enterInFrames = -1;
			return;
		}

		if ( IsActive && _collapsed is not null )
			FitWindow( window, view );

		if ( _enterInFrames >= 0 && _enterInFrames-- == 0 && inGame && !IsActive )
			Enter();
	}

	public static void Enter()
	{
		var window = EditorWindow;
		var view = SceneViewWidget.Current;
		if ( IsActive || !window.IsValid() || !view.IsValid() || !InGameView ) return;
		if ( !TryGetMonitor( window, out var monitor ) ) return;

		_madeViewFullscreen = !window.IsFullscreen( view ) && window.SetFullscreen( view );

		_hidden.Clear();
		_collapsed = new();
		Hide( window.MenuWidget, collapse: true );
		Hide( window.StatusBar, collapse: true );
		foreach ( var tools in view.GetDescendants<ViewportTools>() )
			Hide( tools );
		_monitor = monitor;
		_fitAttempts = 0;
		_fitWait = 2;

		_wasMaximized = window.IsMaximized;
		if ( _wasMaximized )
			window.SetMaximized( false );
		_position = window.Position;
		_size = window.Size;

		// The editor draws its own title bar inside the window (no frame margins), so this covers the monitor exactly.
		window.Position = monitor.Position;
		window.Size = monitor.Size;
		window.Raise();

		// Windows only sends the taskbar behind windows it takes for fullscreen, and the editor's window keeps its
		// caption style, so tell the taskbar directly. It comes back by itself when you switch to another program.
		_handle = FindTopLevel( window );
		MarkFullscreen( _handle, true );

		IsActive = true;
	}

	public static void Exit()
	{
		if ( !IsActive ) return;
		IsActive = false;

		MarkFullscreen( _handle, false );
		_handle = IntPtr.Zero;

		foreach ( var (widget, minimum, maximum) in _collapsed ?? new() )
		{
			if ( !widget.IsValid() ) continue;
			widget.MaximumHeight = maximum;
			widget.MinimumHeight = minimum;
		}
		_collapsed = null;

		foreach ( var widget in _hidden )
		{
			if ( widget.IsValid() )
				widget.Visible = true;
		}
		_hidden.Clear();

		var window = EditorWindow;
		if ( !window.IsValid() ) return;

		window.Position = _position;
		window.Size = _size;
		if ( _wasMaximized )
			window.SetMaximized( true );

		var view = SceneViewWidget.Current;
		if ( _madeViewFullscreen && view.IsValid() && window.IsFullscreen( view ) )
			window.SetFullscreen( view );
		_madeViewFullscreen = false;
	}

	static void Hide( Widget widget, bool collapse = false )
	{
		if ( !widget.IsValid() || !widget.Visible ) return;

		widget.Visible = false;
		_hidden.Add( widget );

		if ( collapse )
		{
			_collapsed.Add( (widget, widget.MinimumHeight, widget.MaximumHeight) );
			widget.FixedHeight = 0;
		}
	}

	/// <summary>
	/// Grow the window past the monitor's top and bottom until the editor's fullscreen view covers the monitor.
	/// </summary>
	static void FitWindow( Widget window, Widget view )
	{
		// The editor lays the view out on its own frame tick, so give it a couple of frames after each change.
		if ( _monitor.Height <= 0 || _fitAttempts >= 10 || _fitWait-- > 0 ) return;

		var have = view.ScreenRect;
		var above = have.Top - _monitor.Top;
		var below = _monitor.Bottom - have.Bottom;
		if ( MathF.Abs( above ) < 0.5f && MathF.Abs( below ) < 0.5f ) return;

		_fitAttempts++;
		_fitWait = 2;
		window.Position -= new Vector2( 0, above );
		window.Size += new Vector2( 0, above + below );
	}

	/// <summary>
	/// The whole monitor the editor is on, taskbar included (Widget.ScreenGeometry is the work area without it).
	/// </summary>
	public static bool TryGetMonitor( Widget window, out Rect rect )
	{
		rect = default;

		var scale = window.DpiScale > 0 ? window.DpiScale : 1f;
		var centre = window.ScreenGeometry.Center * scale;
		var monitor = MonitorFromPoint( new Point32 { X = (int)centre.x, Y = (int)centre.y }, MonitorDefaultToNearest );
		var info = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
		if ( monitor == IntPtr.Zero || !GetMonitorInfo( monitor, ref info ) ) return false;

		var m = info.Monitor;
		rect = new Rect( m.Left / scale, m.Top / scale, (m.Right - m.Left) / scale, (m.Bottom - m.Top) / scale );
		return true;
	}

	/// <summary>
	/// The editor's top-level native window: the one under the middle of its screen, if it's ours.
	/// </summary>
	static IntPtr FindTopLevel( Widget window )
	{
		var scale = window.DpiScale > 0 ? window.DpiScale : 1f;
		var centre = window.ScreenGeometry.Center * scale;
		var handle = GetAncestor( WindowFromPoint( new Point32 { X = (int)centre.x, Y = (int)centre.y } ), GetAncestorRoot );
		if ( IsOurs( handle ) ) return handle;

		handle = GetForegroundWindow();
		return IsOurs( handle ) ? handle : IntPtr.Zero;
	}

	static bool IsOurs( IntPtr handle )
	{
		if ( handle == IntPtr.Zero ) return false;
		GetWindowThreadProcessId( handle, out var processId );
		return processId == Environment.ProcessId;
	}

	static void MarkFullscreen( IntPtr handle, bool fullscreen )
	{
		if ( handle == IntPtr.Zero )
		{
			if ( fullscreen ) Log.Warning( "GameFullscreen: couldn't find the editor's window, so the taskbar stays" );
			return;
		}

		try
		{
			var taskbar = (ITaskbarList2)new TaskbarList();
			taskbar.HrInit();
			taskbar.MarkFullscreenWindow( handle, fullscreen );
		}
		catch ( Exception e )
		{
			Log.Warning( $"GameFullscreen: couldn't move the taskbar out of the way ({e.Message})" );
		}
	}

	const uint MonitorDefaultToNearest = 2;
	const uint GetAncestorRoot = 2;

	[StructLayout( LayoutKind.Sequential )]
	struct Point32 { public int X, Y; }

	[StructLayout( LayoutKind.Sequential )]
	struct Rect32 { public int Left, Top, Right, Bottom; }

	[StructLayout( LayoutKind.Sequential )]
	struct MonitorInfo
	{
		public int Size;
		public Rect32 Monitor;
		public Rect32 Work;
		public uint Flags;
	}

	[DllImport( "user32.dll" )]
	static extern IntPtr MonitorFromPoint( Point32 point, uint flags );

	[DllImport( "user32.dll", EntryPoint = "GetMonitorInfoW" )]
	static extern bool GetMonitorInfo( IntPtr monitor, ref MonitorInfo info );

	[DllImport( "user32.dll" )]
	static extern IntPtr WindowFromPoint( Point32 point );

	[DllImport( "user32.dll" )]
	static extern IntPtr GetAncestor( IntPtr handle, uint flags );

	[DllImport( "user32.dll" )]
	static extern IntPtr GetForegroundWindow();

	[DllImport( "user32.dll" )]
	static extern uint GetWindowThreadProcessId( IntPtr handle, out uint processId );

	[ComImport, Guid( "56FDF344-FD6D-11d0-958A-006097C9A090" )]
	class TaskbarList { }

	[ComImport, Guid( "602D4995-B13A-429b-A66E-1935E44F4317" ), InterfaceType( ComInterfaceType.InterfaceIsIUnknown )]
	interface ITaskbarList2
	{
		void HrInit();
		void AddTab( IntPtr handle );
		void DeleteTab( IntPtr handle );
		void ActivateTab( IntPtr handle );
		void SetActiveAlt( IntPtr handle );
		void MarkFullscreenWindow( IntPtr handle, [MarshalAs( UnmanagedType.Bool )] bool fullscreen );
	}
}
