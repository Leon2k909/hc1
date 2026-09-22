using System.Collections.Generic;

namespace Sandbox;

/// <summary>
/// Input injected by the Claude Bridge. Actions set from the editor thread are cleared before the game
/// reads them, so they are queued here and re-applied at the start of every game frame instead.
/// </summary>
public static class BridgeInput
{
	private static readonly Dictionary<string, RealTimeUntil> held = new();
	private static readonly HashSet<string> pressed = new();

	/// <summary>Hold until released, or until <paramref name="seconds"/> pass when positive.</summary>
	public static void Hold( string action, float seconds )
	{
		lock ( held ) held[action] = seconds > 0f ? seconds : float.MaxValue;
	}

	public static void Press( string action )
	{
		lock ( held ) pressed.Add( action );
	}

	public static void Release( string action )
	{
		lock ( held ) { held.Remove( action ); pressed.Remove( action ); }
	}

	public static void ReleaseAll()
	{
		lock ( held ) { held.Clear(); pressed.Clear(); }
	}

	internal static void Apply()
	{
		lock ( held )
		{
			foreach ( var action in pressed ) Input.SetAction( action, true );
			pressed.Clear();

			List<string> expired = null;
			foreach ( var (action, until) in held )
			{
				if ( until ) (expired ??= new()).Add( action );
				else Input.SetAction( action, true );
			}
			if ( expired is not null ) foreach ( var action in expired ) held.Remove( action );
		}
	}
}

internal sealed class BridgeInputSystem : GameObjectSystem
{
	public BridgeInputSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.StartUpdate, -1000, BridgeInput.Apply, "BridgeInput" );
	}
}
