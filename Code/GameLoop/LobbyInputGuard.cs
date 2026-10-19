namespace Facepunch;

/// <summary>
/// Holds this machine's player to the lobby's input rule (<see cref="GameMode.LobbyInputRule"/>). Playing with the other
/// input warns at once (<see cref="UI.LobbyInputOverlay"/>), and after <see cref="Grace"/> seconds of it a client leaves
/// for the menu. The host is only warned: taking it out would end the match, or hand it to someone else.
/// Only play counts: alive, with no menu, scoreboard or chat open, since a controller player may click a menu with
/// the mouse. Pressing a button of the right input starts the count again.
/// </summary>
public sealed class LobbyInputGuard : GameObjectSystem<LobbyInputGuard>
{
	/// <summary>Seconds of play with the other input before a client leaves.</summary>
	public const float Grace = 15f;

	/// <summary>A stray key or button doesn't warn: the warning shows after this long.</summary>
	public const float WarnAfter = 1f;

	/// <summary>Seconds of play in a row with the other input. Kept over a map change in the same lobby.</summary>
	public static float OffInput { get; private set; }

	/// <summary>The rule being broken, while <see cref="OffInput"/> counts.</summary>
	public static LobbyInput Rule { get; private set; }

	public static bool IsWarning => OffInput >= WarnAfter;
	public static float SecondsLeft => MathF.Max( 0f, Grace - OffInput );

	private static bool _leaving;

	public LobbyInputGuard( Scene scene ) : base( scene )
	{
		Listen( Stage.StartUpdate, 10, Tick, "LobbyInputGuard" );
	}

	private void Tick()
	{
		if ( Scene.IsEditor )
			return;

		if ( !Networking.IsActive )
		{
			OffInput = 0f;
			_leaving = false;
			return;
		}

		var mode = GameMode.Instance;
		if ( !mode.IsValid() || mode.Scene != Scene )
			return;

		if ( Networking.IsHost )
			mode.KeepLobbyInputRule();

		var rule = mode.LobbyInputRule;
		if ( rule == LobbyInput.Any || _leaving )
		{
			OffInput = 0f;
			return;
		}

		// Out of play the count holds where it was: a menu clicked with the mouse doesn't count, either way.
		if ( !IsPlaying() )
			return;

		if ( LobbyInputRules.Device == rule )
		{
			OffInput = 0f;
			return;
		}

		Rule = rule;
		OffInput += Time.Delta;

		if ( OffInput >= Grace && !Networking.IsHost )
			Leave( rule );
	}

	private static bool IsPlaying()
	{
		if ( UI.Toast.IsWinShowing || GameUtils.IsInteractiveMouseUiOpen() || GameUtils.IsGunsmithStudioOpen() )
			return false;

		var client = Client.Local;
		if ( !client.IsValid() )
			return false;

		var pawn = client.PlayerPawn;
		return pawn.IsValid() && pawn.HealthComponent.IsValid() && pawn.HealthComponent.State == LifeState.Alive;
	}

	private static void Leave( LobbyInput rule )
	{
		_leaving = true;
		OffInput = 0f;
		Log.Info( $"Lobby input: leaving a {rule} lobby after {Grace} s playing with the other input" );

		UI.MainMenuRoot.PendingNotice = rule == LobbyInput.Controller
			? "You were taken out of a controller-only lobby for playing with mouse and keyboard."
			: "You were taken out of a mouse and keyboard lobby for playing with a controller.";

		Networking.Disconnect();
		GameUtils.ReturnToMainMenu();
	}
}
