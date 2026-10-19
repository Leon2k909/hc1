namespace Facepunch;

/// <summary>
/// Settings → Controls' sensitivity: scales the look input once a frame, before anything reads it. s&box adds the mouse
/// (scaled by its own mouse sensitivity) and the right stick (by its own look speeds) into <see cref="Input.AnalogLook"/>,
/// so a frame the mouse moved is the mouse's, and any other is the stick's. Moving both at once is taken as the mouse.
/// </summary>
public sealed class LookSensitivitySystem : GameObjectSystem<LookSensitivitySystem>
{
	public LookSensitivitySystem( Scene scene ) : base( scene )
	{
		Listen( Stage.StartUpdate, -1000, Apply, "LookSensitivity" );
	}

	private void Apply()
	{
		// Only the scene being played: another scene's copy of this system would scale the same frame's input again.
		if ( Scene.IsEditor || Scene != Game.ActiveScene )
			return;

		var look = Input.AnalogLook;
		if ( look.pitch == 0f && look.yaw == 0f )
			return;

		Input.AnalogLook = Scale( look, Input.MouseDelta.LengthSquared > 0f, IsAiming() );
	}

	public static Angles Scale( Angles look, bool fromMouse, bool aiming )
	{
		var settings = GameSettingsSystem.Current;
		if ( settings is null )
			return look;

		if ( fromMouse )
		{
			var mouse = settings.MouseSensitivity * (aiming ? settings.MouseAdsSensitivity : 1f);
			return new Angles( look.pitch * mouse, look.yaw * mouse, look.roll );
		}

		var ads = aiming ? settings.ControllerAdsSensitivity : 1f;
		return new Angles( look.pitch * settings.ControllerVerticalSensitivity * ads,
			look.yaw * settings.ControllerHorizontalSensitivity * ads, look.roll );
	}

	/// <summary>The local player's gun is aimed down its sights.</summary>
	private static bool IsAiming()
	{
		var client = Client.Local;
		if ( !client.IsValid() )
			return false;

		var pawn = client.PlayerPawn;
		return pawn.IsValid() && pawn.HasEquipmentTag( "aiming" );
	}
}
