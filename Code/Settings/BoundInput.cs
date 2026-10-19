// Game input is routed through this small facade so player-selected keyboard binds
// can be used by gameplay without changing s&box's private bind collection.
global using Input = Facepunch.BoundInput;

using System;
using System.Collections.Generic;
using System.Linq;
using Sandbox;

namespace Facepunch;

public sealed class SavedControlBindings
{
    public Dictionary<string, string> Keyboard { get; set; } = new( StringComparer.OrdinalIgnoreCase );
}

/// <summary>
/// Local keyboard/mouse bindings. Controller buttons still use the engine input actions.
/// The default path continues to use s&box action input, including any engine-side binds.
/// </summary>
public static class ControlBindings
{
    private const string SavePath = "control-bindings.json";
    private static SavedControlBindings _saved;
    private static Dictionary<string, string> Overrides => (_saved ??= Load()).Keyboard;

    private static SavedControlBindings Load()
    {
        try
        {
            var saved = FileSystem.Data.ReadJson<SavedControlBindings>( SavePath, new() );
            if ( saved?.Keyboard is not null )
            {
                saved.Keyboard = new Dictionary<string, string>( saved.Keyboard, StringComparer.OrdinalIgnoreCase );
                return saved;
            }
        }
        catch ( Exception e )
        {
            Log.Warning( $"Could not load custom keybinds: {e.Message}" );
        }
        return new SavedControlBindings();
    }

    public static bool TryGetOverride( string action, out string key ) => Overrides.TryGetValue( action, out key );

    public static string DisplayKey( string action )
    {
        if ( TryGetOverride( action, out var key ) )
            return string.IsNullOrEmpty( key ) ? null : key;
        return Sandbox.Input.GetButtonOrigin( action, true );
    }

    public static bool MovementOverridden =>
        TryGetOverride( "Forward", out _ ) || TryGetOverride( "Backward", out _ ) ||
        TryGetOverride( "Left", out _ ) || TryGetOverride( "Right", out _ );

    public static bool IsValidKey( string key ) =>
        !string.IsNullOrWhiteSpace( key ) && key.Length <= 64 && !key.Contains( ';' ) &&
        !key.Contains( '\n' ) && !key.Contains( '\r' );

    public static string MakeBinding( string button, bool ctrl, bool shift, bool alt )
    {
        var key = (button ?? "").Trim().ToLowerInvariant();
        key = key switch
        {
            "control" or "leftcontrol" or "rightcontrol" => "ctrl",
            "leftshift" or "rightshift" => "shift",
            "leftalt" or "rightalt" => "alt",
            "mouseleft" => "mouse1",
            "mouseright" => "mouse2",
            "mousemiddle" => "mouse3",
            _ => key
        };

        if ( !IsValidKey( key ) ) return null;
        if ( key is "ctrl" or "shift" or "alt" ) return key;

        var modifiers = new List<string>( 4 );
        if ( ctrl ) modifiers.Add( "ctrl" );
        if ( shift ) modifiers.Add( "shift" );
        if ( alt ) modifiers.Add( "alt" );
        modifiers.Add( key );
        return string.Join( " + ", modifiers );
    }

    public static void Rebind( string action, string binding )
    {
        if ( !string.IsNullOrEmpty( binding ) && !IsValidKey( binding ) ) return;

        var actions = Sandbox.Input.GetActions().ToList();
        var target = actions.FirstOrDefault( x => string.Equals( x.Name, action, StringComparison.OrdinalIgnoreCase ) );
        if ( target is null ) return;

        var oldKey = EffectiveKey( target );
        // Swap conflicting gameplay binds so rebinding (for example) W to Reload
        // doesn't leave both actions on the same key. Spectator keys have their own context.
        if ( !string.IsNullOrEmpty( binding ) )
        {
            var conflict = actions.FirstOrDefault( x =>
                !string.Equals( x.Name, action, StringComparison.OrdinalIgnoreCase ) &&
                !string.Equals( x.GroupName, "Menus", StringComparison.OrdinalIgnoreCase ) &&
                !string.Equals( x.GroupName, "Development", StringComparison.OrdinalIgnoreCase ) &&
                (string.Equals( x.GroupName, "Spectator", StringComparison.OrdinalIgnoreCase ) ==
                 string.Equals( target.GroupName, "Spectator", StringComparison.OrdinalIgnoreCase )) &&
                string.Equals( EffectiveKey( x ), binding, StringComparison.OrdinalIgnoreCase ) );

            if ( conflict is not null )
                Overrides[conflict.Name] = oldKey;
        }

        Overrides[target.Name] = binding ?? "";
        Save();
    }

    private static string EffectiveKey( InputAction action ) =>
        TryGetOverride( action.Name, out var key ) ? key : action.KeyboardCode ?? "";

    public static void Reset()
    {
        Overrides.Clear();
        Save();
    }

    private static void Save()
    {
        try { FileSystem.Data.WriteJson( SavePath, _saved ); }
        catch ( Exception e ) { Log.Warning( $"Could not save custom keybinds: {e.Message}" ); }
    }

    private static string[] Parts( string key ) =>
        key.Split( '+', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries );

    public static bool Held( string key )
    {
        if ( string.IsNullOrEmpty( key ) ) return false;
        return Parts( key ).All( Sandbox.Input.Keyboard.Down );
    }

    public static bool Pressed( string key )
    {
        if ( string.IsNullOrEmpty( key ) ) return false;
        var parts = Parts( key );
        return parts.Length > 0 && parts.All( Sandbox.Input.Keyboard.Down ) &&
            parts.Any( Sandbox.Input.Keyboard.Pressed );
    }

    public static bool Released( string key )
    {
        if ( string.IsNullOrEmpty( key ) ) return false;
        var parts = Parts( key );
        return parts.Length > 0 &&
            parts.Any( Sandbox.Input.Keyboard.Released ) &&
            parts.All( k => Sandbox.Input.Keyboard.Down( k ) || Sandbox.Input.Keyboard.Released( k ) );
    }
}

/// <summary>
/// Drop-in action facade. Rebound keys are read from raw input, and their actions
/// are also updated in s&box's active command so replicated action bits follow them.
/// </summary>
public static class BoundInput
{
    private static bool Override( string action, out string key )
    {
        key = null;
        return !Sandbox.Input.UsingController && ControlBindings.TryGetOverride( action, out key );
    }

    private static bool Blocked => Sandbox.Input.Suppressed || Sandbox.Input.MouseCursorVisible;

    private static void SetOverrideAction( string action, string key )
    {
        var down = !Blocked && ControlBindings.Held( key );
        Sandbox.Input.SetAction( action, down );
        Sandbox.Input.SetLastAction( action,
            down ? !ControlBindings.Pressed( key ) : ControlBindings.Released( key ) );
    }

    public static bool Down( string action, bool complainOnMissing = true )
    {
        if ( !Override( action, out var key ) ) return Sandbox.Input.Down( action, complainOnMissing );
        SetOverrideAction( action, key );
        return !Blocked && ControlBindings.Held( key );
    }

    public static bool Pressed( string action )
    {
        if ( !Override( action, out var key ) ) return Sandbox.Input.Pressed( action );
        SetOverrideAction( action, key );
        return !Blocked && ControlBindings.Pressed( key );
    }

    public static bool Released( string action )
    {
        if ( !Override( action, out var key ) ) return Sandbox.Input.Released( action );
        SetOverrideAction( action, key );
        return !Blocked && ControlBindings.Released( key );
    }

    public static Vector3 AnalogMove
    {
        get
        {
            if ( Sandbox.Input.UsingController || !ControlBindings.MovementOverridden )
                return Sandbox.Input.AnalogMove;
            if ( Blocked ) return Vector3.Zero;
            var forward = (Down( "Forward" ) ? 1f : 0f) - (Down( "Backward" ) ? 1f : 0f);
            var left = (Down( "Left" ) ? 1f : 0f) - (Down( "Right" ) ? 1f : 0f);
            return new Vector3( forward, left, 0f ).Normal;
        }
    }

    public static Angles AnalogLook { get => Sandbox.Input.AnalogLook; set => Sandbox.Input.AnalogLook = value; }
    public static Vector2 MouseDelta => Sandbox.Input.MouseDelta;
    public static Vector2 MouseWheel => Sandbox.Input.MouseWheel;
    public static bool UsingController => Sandbox.Input.UsingController;
    public static bool MouseCursorVisible => Sandbox.Input.MouseCursorVisible;
    public static bool EscapePressed { get => Sandbox.Input.EscapePressed; set => Sandbox.Input.EscapePressed = value; }
    public static bool Suppressed { get => Sandbox.Input.Suppressed; set => Sandbox.Input.Suppressed = value; }
    public static bool EnableVirtualCursor { get => Sandbox.Input.EnableVirtualCursor; set => Sandbox.Input.EnableVirtualCursor = value; }
    public static float GetAnalog( InputAnalog analog ) => Sandbox.Input.GetAnalog( analog );
    public static IEnumerable<InputAction> GetActions() => Sandbox.Input.GetActions();
    public static string GetButtonOrigin( string action, bool ignoreController = false ) =>
        !Sandbox.Input.UsingController || ignoreController
            ? ControlBindings.DisplayKey( action )
            : Sandbox.Input.GetButtonOrigin( action, ignoreController );
    public static Texture GetGlyph( string action, InputGlyphSize size = InputGlyphSize.Medium, bool outline = false )
    {
        if ( Override( action, out var key ) )
            return string.IsNullOrEmpty( key ) ? null : Sandbox.Input.Keyboard.GetGlyph( key, size, outline );
        return Sandbox.Input.GetGlyph( action, size, outline );
    }
    public static Texture GetGlyph( string action, InputGlyphSize size, GlyphStyle style ) =>
        Sandbox.Input.GetGlyph( action, size, style );
    public static Texture GetGlyph( string action, GlyphStyle style, InputGlyphSize size = InputGlyphSize.Medium ) =>
        Sandbox.Input.GetGlyph( action, size, style );
    public static void Clear( string action ) => Sandbox.Input.Clear( action );
    public static void ReleaseAction( string action ) => Sandbox.Input.ReleaseAction( action );
    public static void TriggerHaptics( HapticEffect effect, float duration, float strength, float speed ) =>
        Sandbox.Input.TriggerHaptics( effect, duration, strength, speed );

    public static class Keyboard
    {
        public static bool Down( string key ) => Sandbox.Input.Keyboard.Down( key );
        public static bool Pressed( string key ) => Sandbox.Input.Keyboard.Pressed( key );
        public static bool Released( string key ) => Sandbox.Input.Keyboard.Released( key );
        public static Texture GetGlyph( string key, InputGlyphSize size, bool outline = false ) =>
            Sandbox.Input.Keyboard.GetGlyph( key, size, outline );
    }
}
